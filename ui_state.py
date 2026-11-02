"""UI state synchronization. Workers return plain data; only the Tk thread updates widgets."""

import queue
import threading
import time
from decimal import Decimal, InvalidOperation

from serialization import dumps


class DesktopView:
    def build(self):
        from ui_layout import build

        self.view_queue = queue.Queue()
        self.poll_pending = False
        self.closing = self.closed = False
        self.last_view, self.view_revision = None, -1
        self.scan_state = {"active": False}
        build(self)

    def navigate(self, key):
        titles = {
            "search": "Memory search",
            "watches": "Live watches",
            "snapshots": "Snapshots",
            "ai": "AI connection",
            "activity": "Session activity",
        }
        self.current_page = key
        self.page_shells[key].tkraise()
        self.page_title.configure(text=titles[key])
        for name, button in self.nav.items():
            button.configure(style="Selected.Nav.TButton" if name == key else "Nav.TButton")

    def sort_table(self, tree, column):
        reverse = self.sorts.get(tree, ("", True)) == (column, False)
        self.sorts[tree] = (column, reverse)

        def value(item):
            raw = tree.set(item, column)
            try:
                number = int(raw, 16) if raw.startswith("0x") else Decimal(raw)
                if isinstance(number, Decimal) and not number.is_finite():
                    return (1, raw.lower())
                return (0, number)
            except (ValueError, InvalidOperation):
                return (1, raw.lower())

        for index, item in enumerate(sorted(tree.get_children(), key=value, reverse=reverse)):
            tree.move(item, "", index)

    def fill(self, tree, rows):
        meta = self.tables[tree]
        if rows == meta["rows"]:
            return
        previous = {i: tree.item(i, "values") for i in tree.get_children()}
        selection, scroll = tree.selection(), tree.yview()
        ids = []
        for index, row in enumerate(rows):
            key = "r:" + str(row.get("address", row.get("name", index)))
            ids.append(key)
            values = tuple(str(row.get(c, "")) for c in tree["columns"])
            tags = ["odd" if index % 2 else "even"]
            if row.get("state") == "changed" or (
                tree is getattr(self, "watches", None)
                and key in previous
                and values != previous[key]
            ):
                tags.append("changed")
            if row.get("outcome") == "failed" or row.get("state") in {
                "unreadable",
                "removed",
                "type changed",
                "baseline unreadable",
            }:
                tags.append("failed")
            if tree.exists(key):
                tree.item(key, values=values, tags=tags)
            else:
                tree.insert("", "end", iid=key, values=values, tags=tags)
        keep = set(ids)
        for key in previous:
            if key not in keep:
                tree.delete(key)
        for index, key in enumerate(ids):
            tree.move(key, "", index)
        if tree in self.sorts:
            column, reverse = self.sorts[tree]
            self.sorts[tree] = (column, not reverse)
            self.sort_table(tree, column)
        for key in selection:
            if tree.exists(key):
                tree.selection_add(key)
        if scroll:
            tree.yview_moveto(scroll[0])
        if rows:
            meta["placeholder"].place_forget()
        else:
            meta["placeholder"].place(relx=0.5, rely=0.48, anchor="center")
        meta["rows"] = [dict(r) for r in rows]

    def request_view(self):
        if self.poll_pending or self.closing:
            return
        self.poll_pending = True

        def poll():
            result, error = None, None
            if self.session.lock.acquire(blocking=False):
                try:
                    result = self.session.do_overview()
                except Exception as e:
                    error = str(e)
                finally:
                    self.session.lock.release()
            self.view_queue.put((result, error))

        threading.Thread(target=poll, daemon=True).start()

    def apply_view(self, view):
        self.last_view = view
        s = view["status"]
        pid = s["pid"]
        self.target.set(f"{s['name']}  /  PID {pid}" if pid else "No target attached")
        self.target_detail.set(
            (
                "Read-only process handle · local MCP available"
                if s["alive"]
                else "Target exited. Attach a running process to continue."
            )
            if pid
            else "Filter by process name or PID, then choose a process"
        )
        self.metrics[0].set(f"{s['matches']:,}" if s["scan"] else "—")
        self.metrics[1].set(str(len(view["watches"])))
        scan = s.get("scan")
        self.metrics[2].set(
            "Complete" if scan and scan.get("complete") else "Partial" if scan else "Not scanned"
        )
        if s["revision"] != self.view_revision:
            self.fill(self.results, view["results"])
            self.view_revision = s["revision"]
        self.fill(self.watches, view["watches"])
        self.fill(self.snapshot_table, view["snapshots"])
        self.fill(
            self.activity,
            [
                {
                    "time": time.strftime("%H:%M:%S", time.localtime(e["time"])),
                    "action": e["action"],
                    "outcome": e["outcome"],
                    "details": e.get("error") or dumps(e["args"]),
                }
                for e in reversed(s["audit"])
            ],
        )
        self.update_controls()

    def update_controls(self):
        v = self.last_view or {
            "status": {"alive": False, "matches": 0},
            "watches": [],
            "snapshots": [],
        }
        s = v["status"]
        idle = not self.busy and not self.scan_state.get("active") and not self.closing
        alive = s["alive"]
        rules = {
            "scan": idle and alive,
            "refine": idle and alive and bool(s["matches"]),
            "watch_selected": idle and alive and bool(self.results.selection()),
            "watch_manual": idle and alive,
            "unwatch": idle and bool(self.watches.selection()),
            "copy_result": bool(self.results.selection()),
            "copy_watch": bool(self.watches.selection()),
            "snapshot": idle and alive and bool(v["watches"]),
            "compare": idle and alive and bool(v["snapshots"]),
            "attach": idle and self.process_box.get() in self.proc_map,
            "detach": idle and bool(s.get("pid")),
            "delete_snapshot": idle and bool(v["snapshots"]),
            "refresh": idle,
            "export": idle,
            "cancel": self.scan_state.get("active", False) and not self.closing,
        }
        for key, b in self.buttons.items():
            b.configure(state="normal" if rules.get(key, idle) else "disabled")
        self.buttons["refine"].configure(text=f"Refine {s.get('type', 'int32')} candidates")

    def selected(self, tree):
        items = tree.selection()
        return dict(zip(tree["columns"], tree.item(items[0], "values"))) if items else None

    def copy_address(self, tree):
        row = self.selected(tree)
        if row:
            self.root.clipboard_clear()
            self.root.clipboard_append(row["address"])
            self.status.set("Address copied")

    def select_snapshot(self, event=None):
        row = self.selected(self.snapshot_table)
        if row:
            self.snapshot.set(row["name"])

    def select_watch(self, event=None):
        row = self.selected(self.watches)
        if row:
            self.address.set(row["address"])
            self.label.set(row["label"])
            self.watch_kind.set(row["type"])

    def show_error(self, message):
        self.banner_text.configure(text=str(message)[:1400])
        self.banner.grid()
        self.status.set(
            "Operation failed. Review the message above; previous session data is retained."
        )

    def callback_error(self, kind, value, tb):
        import traceback

        from backend import HOME

        (HOME / "cheatcraft-error.log").write_text(
            "".join(traceback.format_exception(kind, value, tb)), encoding="utf-8"
        )
        self.show_error(str(value))
