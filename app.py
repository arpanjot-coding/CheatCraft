import json
import queue
import threading

from tk_runtime import prepare

prepare()
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as tb

from backend import CONFIG, HOME, Session, start_bridge
from instance import InstanceLock
from storage import write_json
from ui_state import DesktopView
from version import VERSION


class App(DesktopView):
    def __init__(self, session=None):
        self.instance = InstanceLock(CONFIG.with_suffix(".lock"))
        self.session = session
        try:
            self._initialize()
        except Exception:
            listener = getattr(self, "listener", None)
            if listener:
                pipe = listener.address
                listener.close()
                try:
                    if (
                        CONFIG.exists()
                        and json.loads(CONFIG.read_text(encoding="utf-8"))["pipe"] == pipe
                    ):
                        CONFIG.unlink()
                except (OSError, ValueError, KeyError):
                    pass
            if self.session is not None:
                self.session.close()
            if hasattr(self, "root"):
                self.root.destroy()
            self.instance.close()
            raise

    def _initialize(self):
        self.root = tb.Window(
            themename="darkly",
            title=f"CheatCraft {VERSION} — Game Diagnostics",
            size=(1360, 880),
            minsize=(1100, 740),
        )
        self.root.option_add("*Font", "{Segoe UI} 10")
        self.session = self.session or Session()
        self.listener = start_bridge(self.session)
        self.jobs = queue.Queue()
        self.busy = False
        self.operation_done = threading.Event()
        self.operation_done.set()
        self.proc_map = {}
        self.kind = tk.StringVar(value="int32")
        self.value = tk.StringVar(value="")
        self.start = tk.StringVar(value="0x0")
        self.end = tk.StringVar(value="0x7fffffff0000")
        self.status = tk.StringVar(value="Ready · Select a process to begin")
        self.target = tk.StringVar(value="No process attached")
        self.snapshot = tk.StringVar(value="baseline")
        self.address = tk.StringVar()
        self.label = tk.StringVar(value="value")
        self.refine_mode = tk.StringVar(value="equal")
        self.process_filter = tk.StringVar()
        self.build()
        self.refresh_processes()
        self.root.after(100, self.drain)
        self.root.after(1000, self.tick)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.process_filter.trace_add("write", lambda *_: self.filter_processes())
        self.root.bind("<Escape>", lambda _: self.cancel_scan())
        self.root.bind("<Control-f>", lambda _: self.filter_entry.focus_set())
        self.root.bind("<Control-r>", lambda _: self.refresh_processes())
        self.root.report_callback_exception = self.callback_error

    def run(self, action, callback=lambda r: None, **args):
        if self.busy or self.closing or self.scan_state.get("active"):
            self.status.set("Another operation is active. Wait or cancel the scan first.")
            return
        self.busy = True
        self.operation_done.clear()
        self.banner.grid_remove()
        self.status.set("Working · " + action)
        self.progress.start()
        self.update_controls()

        def worker():
            try:
                self.jobs.put((callback, self.session.call(action, **args), None))
            except Exception as e:
                self.jobs.put((callback, None, str(e)))
            finally:
                self.operation_done.set()

        threading.Thread(target=worker, daemon=True).start()

    def drain(self):
        try:
            while True:
                callback, result, error = self.jobs.get_nowait()
                self.busy = False
                self.progress.stop()
                if error:
                    self.show_error(error)
                elif not self.closing:
                    self.status.set("Ready · operation complete")
                    callback(result)
                    self.request_view()
        except queue.Empty:
            pass
        except Exception as e:
            self.show_error(str(e))
        try:
            while True:
                result, error = self.view_queue.get_nowait()
                self.poll_pending = False
                if result and not self.closing:
                    self.apply_view(result)
                elif error and not self.closing:
                    self.show_error(error)
        except queue.Empty:
            pass
        except Exception as e:
            self.show_error(str(e))
        if self.closing and getattr(self, "cleanup_done", False):
            self.closed = True
            self.instance.close()
            self.root.destroy()
            return
        self.scan_state = self.session.call("scan_progress")
        self.update_controls()
        self.root.after(60, self.drain)

    def refresh_processes(self):
        def done(rows):
            self.proc_map = {f"{r['name']}  ·  {r['pid']}": r["pid"] for r in rows}
            self.filter_processes()

        self.run("processes", done)

    def filter_processes(self):
        query = self.process_filter.get().strip().lower()
        self.process_box["values"] = [name for name in self.proc_map if query in name.lower()]
        self.update_controls()

    def cancel_scan(self):
        result = self.session.call("cancel_scan")
        self.status.set(
            "Cancellation requested · previous candidates will be preserved"
            if result["active"]
            else "No scan is running"
        )

    def attached(self, result):
        self.start.set("0x0")
        self.end.set("0x7fffffff0000")
        self.target.set(
            f"Attached PID {result['pid']} · read-only process handle · MCP bridge available"
        )
        self.fill(self.results, [])
        self.fill(self.watches, [])
        self.fill(self.comparison, [])
        self.request_view()

    def attach(self):
        pid = self.proc_map.get(self.process_box.get())
        if pid:
            self.run("attach", self.attached, pid=pid)
        else:
            self.show_error("Select a process from the list before attaching.")

    def detach(self):
        self.run("detach", self.attached)

    def search(self, refine):
        try:
            args = {"value": self.value.get()}
            if refine:
                args["mode"] = self.refine_mode.get()
            if not refine:
                args.update(
                    kind=self.kind.get(), start=int(self.start.get(), 0), end=int(self.end.get(), 0)
                )

            def done(result):
                self.fill(self.results, result["results"])
                stats = result.get("stats", {})
                detail = stats.get("reason", "finished")
                if "bytes" in stats:
                    detail += f" · {stats['bytes'] / 1048576:.2f} MiB · {stats.get('elapsed_seconds', 0):.2f}s"
                if not stats.get("complete", True):
                    detail += " · INCOMPLETE"
                if stats.get("skipped_bytes"):
                    detail += f" · {stats['skipped_bytes']} unreadable bytes"
                if result.get("preserved_previous"):
                    detail += " · previous candidates preserved"
                self.status.set(
                    f"{result['matches']:,} matches · showing {len(result['results']):,} · {detail}"
                )
                self.tables[self.results]["placeholder"].configure(
                    text="No matching candidates\nTry another value, type or address range."
                )

            self.run("refine" if refine else "scan", done, **args)
        except ValueError:
            self.show_error("Use decimal or 0x-prefixed hexadecimal range addresses.")

    def watch_selected(self):
        selection = self.results.selection()
        if selection:
            a, kind, _ = self.results.item(selection[0], "values")
            self.run("watch", address=a, kind=kind, label=self.label.get())

    def watch_manual(self):
        self.run(
            "watch", address=self.address.get(), kind=self.watch_kind.get(), label=self.label.get()
        )

    def unwatch(self):
        selected = self.watches.selection()
        if selected:
            self.run("unwatch", address=self.selected(self.watches)["address"])

    def captured(self, result):
        self.status.set(f"Captured {len(result['values'])} watched values as {self.snapshot.get()}")

    def compared(self, result):
        self.fill(self.comparison, result)
        self.status.set(f"Compared {len(result)} watched values against {self.snapshot.get()}")

    def delete_snapshot(self):
        def done(result):
            self.fill(self.comparison, [])
            self.status.set(f"Deleted snapshot {result['deleted']}")

        self.run("delete_snapshot", done, name=self.snapshot.get())

    def export(self):
        if self.busy or self.closing or self.scan_state.get("active"):
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".json",
            initialfile="cheatcraft-session.json",
            filetypes=[("JSON", "*.json")],
        )
        if path:

            def write(data):
                self.busy = True
                self.operation_done.clear()

                def worker():
                    try:
                        write_json(path, data)
                        self.jobs.put((lambda _: self.status.set("Session exported"), None, None))
                    except Exception as e:
                        self.jobs.put((lambda _: None, None, str(e)))
                    finally:
                        self.operation_done.set()

                threading.Thread(target=worker, daemon=True).start()

            self.run("export", write)

    def copy_config(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.mcp_json)
        self.status.set("MCP configuration copied")

    def tick(self):
        if self.closing or self.closed:
            return
        progress = self.session.call("scan_progress")
        if progress.get("active"):
            detail = (
                f"{progress.get('bytes', 0) / 1048576:.1f} MiB"
                if progress.get("operation") == "search"
                else f"{progress.get('processed', 0):,}/{progress.get('total', 0):,} candidates"
            )
            self.status.set(
                f"Scanning · {detail} · {progress.get('matches', 0):,} matches · Esc to cancel"
            )
        self.request_view()
        self.root.after(600, self.tick)

    def close(self):
        if self.closing or self.closed:
            return
        self.closing = True
        self.session.begin_close()
        self.status.set("Closing · cancelling active work and releasing handles")
        self.update_controls()

        def cleanup():
            try:
                self.operation_done.wait()
                with self.session.lock:
                    pipe = self.listener.address
                    self.listener.close()
                    self.session.close()
                    if CONFIG.exists():
                        config = json.loads(CONFIG.read_text(encoding="utf-8"))
                        if config["pipe"] == pipe:
                            CONFIG.unlink()
            except Exception as e:
                (HOME / "cheatcraft-error.log").write_text(str(e), encoding="utf-8")
            finally:
                self.cleanup_done = True

        threading.Thread(target=cleanup, daemon=True).start()


if __name__ == "__main__":
    from multiprocessing import freeze_support

    freeze_support()
    try:
        App().root.mainloop()
    except Exception:
        import traceback

        details = traceback.format_exc()
        log = HOME / "cheatcraft-error.log"
        log.write_text(details, encoding="utf-8")
        messagebox.showerror(
            "CheatCraft could not start",
            "Details were saved to " + str(log) + "\n\n" + details.splitlines()[-1],
        )
