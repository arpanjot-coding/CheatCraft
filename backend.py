import copy
import json
import os
import secrets
import sys
import threading
import time
from multiprocessing import AuthenticationError
from multiprocessing.connection import Client, Listener
from pathlib import Path

import psutil

from memory import Process, pack, processes, unpack
from serialization import dumps
from storage import write_json
from version import VERSION

HOME = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
CONFIG = Path(os.environ.get("CHEATCRAFT_SESSION_FILE", str(HOME / "session.json")))


class Session:
    def __init__(self):
        self.lock = threading.RLock()
        self.process = None
        self.hits = []
        self.kind = "int32"
        self.watches = {}
        self.snapshots = {}
        self.audit = []
        self.baseline = {}
        self.cancel = threading.Event()
        self.progress = {"active": False}
        self.revision = 0
        self.last_scan = None
        self.closed = False
        self.shutdown = threading.Event()

    def call(self, action, **args):
        if action == "cancel_scan":
            self.cancel.set()
            return {"requested": True, "active": self.progress.get("active", False)}
        if action == "scan_progress":
            return dict(self.progress)
        with self.lock:
            if self.closed or self.shutdown.is_set():
                raise RuntimeError("This desktop session has closed. Reconnect to CheatCraft.")
            event = None
            if action not in {"status", "watches", "processes", "overview", "export"}:
                event = {"time": time.time(), "action": action, "args": args, "outcome": "running"}
                self.audit.append(event)
                self.audit = self.audit[-200:]
            try:
                result = getattr(self, "do_" + action)(**args)
                if event is not None:
                    event["outcome"] = "completed"
                    self.revision += 1
                return result
            except Exception as e:
                if event is not None:
                    event.update(outcome="failed", error=str(e))
                raise

    def do_processes(self):
        return processes()

    def do_attach(self, pid):
        new = Process(int(pid))
        if self.process:
            self.process.close()
        self.process = new
        self.hits, self.watches, self.snapshots = [], {}, {}
        self.baseline = {}
        self.last_scan = None
        return self.do_status()

    def do_detach(self):
        if self.process:
            self.process.close()
        self.process = None
        self.hits, self.watches, self.snapshots = [], {}, {}
        self.baseline = {}
        self.last_scan = None
        return self.do_status()

    def do_status(self):
        alive, name = False, "No target"
        if self.process:
            try:
                self.process.alive()
                alive = True
            except RuntimeError:
                name = "Target exited"
            if alive:
                try:
                    name = psutil.Process(self.process.pid).name()
                except psutil.Error:
                    name = f"Process {self.process.pid}"
        return {
            "pid": self.process.pid if self.process else None,
            "type": self.kind,
            "matches": len(self.hits),
            "name": name,
            "alive": alive,
            "revision": self.revision,
            "scan": copy.deepcopy(self.last_scan),
            "audit": copy.deepcopy(self.audit[-30:]),
        }

    def do_overview(self):
        return {
            "status": self.do_status(),
            "results": self.rows(self.hits[:1000], observed=True),
            "watches": self.do_watches(),
            "snapshots": [
                {"name": name, "time": s["time"], "count": len(s["values"])}
                for name, s in self.snapshots.items()
            ],
        }

    def do_export(self):
        return copy.deepcopy(
            {
                "schema_version": 1,
                "app_version": VERSION,
                "status": self.do_status(),
                "watches": self.do_watches(),
                "snapshots": self.snapshots,
                "audit": self.audit,
            }
        )

    def require(self):
        if not self.process:
            raise ValueError("Attach a process in the desktop app first.")
        self.process.alive()
        return self.process

    def do_scan(self, kind, value, start=0, end=0x7FFFFFFF0000):
        p = self.require()
        pack(kind, value)
        start, end = int(start), int(end)
        if start < 0 or end <= start or end > 0x7FFFFFFF0000:
            raise ValueError("Invalid address range.")
        self.cancel.clear()
        if self.shutdown.is_set():
            raise RuntimeError("The desktop session is closing.")
        self.progress = {"active": True, "operation": "search", "bytes": 0, "matches": 0}
        observed = {}
        try:
            hits, stats = p.search(
                kind,
                value,
                start,
                end,
                cancel=self.cancel,
                observed=observed,
                progress=lambda r: setattr(
                    self, "progress", {**r, "active": True, "operation": "search"}
                ),
            )
        finally:
            self.progress = {**self.progress, "active": False}
        self.progress = {**stats, "active": False}
        if stats["reason"] == "cancelled":
            return {
                "stats": stats,
                "matches": len(self.hits),
                "results": self.rows(self.hits[:1000]),
                "preserved_previous": True,
            }
        self.kind, self.hits = kind, hits
        self.baseline = observed
        self.last_scan = {
            "kind": kind,
            "value": str(value),
            "start": hex(start),
            "end": hex(end),
            **stats,
        }
        return {"stats": stats, "matches": len(hits), "results": self.rows(hits[:1000])}

    def rows(self, addresses, observed=False):
        rows = []
        for a in addresses:
            try:
                value = (
                    unpack(self.kind, self.baseline[a])
                    if observed
                    else self.require().value(a, self.kind)
                )
            except (OSError, RuntimeError):
                value = "unreadable"
            rows.append({"address": hex(a), "value": value, "type": self.kind})
        return rows

    def do_refine(self, value="", mode="equal"):
        p = self.require()
        if mode not in {"equal", "changed", "unchanged", "increased", "decreased"}:
            raise ValueError(
                "Refinement mode must be equal, changed, unchanged, increased, or decreased."
            )
        if not self.baseline:
            raise ValueError("Run an exact search before refining candidates.")
        expected = pack(self.kind, value) if mode == "equal" else None
        self.cancel.clear()
        if self.shutdown.is_set():
            raise RuntimeError("The desktop session is closing.")
        self.progress = {
            "active": True,
            "operation": "refine",
            "processed": 0,
            "total": len(self.hits),
        }
        hits, observed, skipped = [], {}, 0
        try:
            for index, a in enumerate(self.hits):
                if self.cancel.is_set():
                    return {
                        "matches": len(self.hits),
                        "results": self.rows(self.hits[:1000]),
                        "stats": {"reason": "cancelled", "complete": False},
                        "preserved_previous": True,
                    }
                try:
                    before = self.baseline[a]
                    now = p.read(a, len(before))
                    keep = (
                        (mode == "equal" and now == expected)
                        or (mode == "changed" and now != before)
                        or (mode == "unchanged" and now == before)
                        or (
                            mode == "increased"
                            and unpack(self.kind, now) > unpack(self.kind, before)
                        )
                        or (
                            mode == "decreased"
                            and unpack(self.kind, now) < unpack(self.kind, before)
                        )
                    )
                    if keep:
                        hits.append(a)
                        observed[a] = now
                except OSError:
                    skipped += 1
                self.progress = {**self.progress, "processed": index + 1, "matches": len(hits)}
        finally:
            self.progress = {**self.progress, "active": False}
        if self.cancel.is_set():
            return {
                "matches": len(self.hits),
                "results": self.rows(self.hits[:1000]),
                "stats": {"reason": "cancelled", "complete": False},
                "preserved_previous": True,
            }
        self.hits = hits
        self.baseline = observed
        if self.last_scan:
            self.last_scan = {
                **self.last_scan,
                "last_refinement": mode,
                "unreadable_candidates": skipped,
            }
        return {
            "matches": len(hits),
            "results": self.rows(hits[:1000]),
            "stats": {
                "reason": "finished",
                "complete": skipped == 0,
                "unreadable_candidates": skipped,
                "mode": mode,
            },
        }

    def do_watch(self, address, kind, label="value"):
        a = int(address, 0) if isinstance(address, str) else int(address)
        if len(self.watches) >= 256 and hex(a) not in self.watches:
            raise ValueError("Watch limit reached (256).")
        value = self.require().value(a, kind)
        self.watches[hex(a)] = {"type": kind, "label": str(label)[:80]}
        return {"address": hex(a), "value": value}

    def do_watches(self):
        rows = []
        for a, w in self.watches.items():
            try:
                value = self.require().value(int(a, 16), w["type"])
            except (OSError, RuntimeError):
                value = "unreadable / exited"
            rows.append({"address": a, **w, "value": value})
        return rows

    def do_unwatch(self, address):
        self.watches.pop(hex(int(address, 0)), None)
        return self.do_watches()

    def do_snapshot(self, name):
        if not name or len(name) > 80:
            raise ValueError("Snapshot name must be 1–80 characters.")
        if len(self.snapshots) >= 50 and name not in self.snapshots:
            raise ValueError("Snapshot limit reached (50).")
        if not self.watches:
            raise ValueError("Add at least one watch before capturing a snapshot.")
        self.snapshots[name] = {
            "time": time.time(),
            "pid": self.require().pid,
            "values": self.do_watches(),
        }
        return self.snapshots[name]

    def do_compare(self, name):
        if name not in self.snapshots:
            raise ValueError("Choose an existing snapshot to compare.")
        old = self.snapshots[name]
        current = {r["address"]: r for r in self.do_watches()}
        rows = []
        for r in old["values"]:
            now = current.get(r["address"])
            after = now["value"] if now else "watch removed"
            state = (
                "removed"
                if now is None
                else "type changed"
                if now["type"] != r["type"]
                else "unreadable"
                if isinstance(after, str)
                else "baseline unreadable"
                if isinstance(r["value"], str)
                else "unchanged"
                if after == r["value"]
                else "changed"
            )
            rows.append(
                {
                    "address": r["address"],
                    "label": r["label"],
                    "before": r["value"],
                    "after": after,
                    "state": state,
                    "type": r["type"],
                }
            )
        return rows

    def do_delete_snapshot(self, name):
        if name not in self.snapshots:
            raise ValueError("Choose an existing snapshot to delete.")
        del self.snapshots[name]
        return {"deleted": name}

    def begin_close(self):
        self.shutdown.set()
        self.cancel.set()

    def close(self):
        self.begin_close()
        self.closed = True
        if self.process:
            self.process.close()


def start_bridge(session, config_path=CONFIG):
    key = secrets.token_bytes(32)
    pipe = r"\\.\pipe\CheatCraft-" + secrets.token_hex(12)
    listener = Listener(pipe, family="AF_PIPE", authkey=key)
    try:
        write_json(config_path, {"pipe": pipe, "key": key.hex()})
    except Exception:
        listener.close()
        raise
    allowed = {
        "status",
        "scan",
        "refine",
        "watch",
        "watches",
        "snapshot",
        "compare",
        "unwatch",
        "cancel_scan",
        "scan_progress",
    }
    slots = threading.BoundedSemaphore(8)

    def handle(conn):
        try:
            if not conn.poll(5):
                raise TimeoutError("No request received.")
            request = json.loads(conn.recv_bytes(1024 * 1024))
            action = request["action"]
            if action not in allowed:
                raise ValueError("Action requires desktop control.")
            result = session.call(action, **request.get("args", {}))
            conn.send_bytes(dumps({"result": result}).encode("utf-8"))
        except Exception as e:
            try:
                conn.send_bytes(dumps({"error": str(e)}).encode("utf-8"))
            except OSError:
                pass
        finally:
            conn.close()
            slots.release()

    def serve():
        while True:
            try:
                conn = listener.accept()
                if not slots.acquire(blocking=False):
                    conn.close()
                    continue
                threading.Thread(target=handle, args=(conn,), daemon=True).start()
            except AuthenticationError:
                continue
            except (OSError, EOFError):
                break

    threading.Thread(target=serve, daemon=True).start()
    return listener


def remote(action, **args):
    try:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        with Client(config["pipe"], family="AF_PIPE", authkey=bytes.fromhex(config["key"])) as conn:
            conn.send_bytes(dumps({"action": action, "args": args}).encode("utf-8"))
            if not conn.poll(120):
                raise TimeoutError("Desktop operation did not finish within 120 seconds.")
            result = json.loads(conn.recv_bytes(1024 * 1024))
    except (OSError, EOFError, AuthenticationError, json.JSONDecodeError) as e:
        raise RuntimeError(
            "Cannot reach the CheatCraft desktop. Open the app, attach a target, then reconnect your MCP client."
        ) from e
    if "error" in result:
        raise ValueError(result["error"])
    return result["result"]
