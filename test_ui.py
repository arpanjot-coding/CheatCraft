"""Widget-level integration smoke test; uses a separate MCP session file."""

import os
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch


def main():
    with tempfile.TemporaryDirectory() as folder:
        os.environ["CHEATCRAFT_SESSION_FILE"] = str(Path(folder) / "ui-session.json")
        from app import App
        from test_support import HarnessSession

        session = HarnessSession()
        info = session.call("sample")
        app = App(session=session)
        app.root.withdraw()

        def settle():
            deadline = time.monotonic() + 15
            while (app.busy or app.poll_pending) and time.monotonic() < deadline:
                app.root.update()
                time.sleep(0.01)
            assert not app.busy, "UI operation timed out"

        try:
            settle()
            assert app.proc_map
            app.process_filter.set("python")
            assert all("python" in str(v).lower() for v in app.process_box["values"])
            app.process_filter.set("")
            assert not hasattr(app, "sample")
            assert not {"sample", "damage", "reset"} & app.buttons.keys()
            target = next(name for name, pid in app.proc_map.items() if pid == info["pid"])
            app.process_box.set(target)
            app.attach()
            settle()
            app.start.set(hex(info["start"]))
            app.end.set(hex(info["end"]))
            app.value.set("137")
            app.search(False)
            settle()
            rows = app.results.get_children()
            assert len(rows) == 1, app.status.get()
            app.results.selection_set(rows[0])
            app.watch_selected()
            settle()
            app.run("snapshot", app.captured, name="baseline")
            settle()
            session.call("sample_change", command="damage")
            app.run("compare", app.compared, name="baseline")
            settle()
            values = app.comparison.item(app.comparison.get_children()[0], "values")
            assert values[1:3] == ("137", "130"), values
            app.value.set("130")
            app.refine_mode.set("decreased")
            app.search(True)
            settle()
            assert len(app.results.get_children()) == 1
            app.refine_mode.set("unchanged")
            app.search(True)
            settle()
            assert len(app.results.get_children()) == 1
            app.watch_kind.set("float32")
            assert app.kind.get() == "int32", "Watch type must not change scan type"
            # A scan invoked outside the UI (as MCP does) must update desktop candidates.
            info = app.session.sample_info
            app.session.call(
                "scan", kind="uint32", value="42", start=info["start"], end=info["end"]
            )
            app.request_view()
            settle()
            rows = app.results.get_children()
            assert app.results.item(rows[0], "values")[1] == "uint32"
            # Watch reads must never occur on Tk's event thread.
            original = app.session.process.value
            main_thread = threading.get_ident()
            calls = []

            def checked(*args):
                calls.append(threading.get_ident())
                assert threading.get_ident() != main_thread
                return original(*args)

            with patch.object(app.session.process, "value", side_effect=checked):
                app.request_view()
                settle()
            assert calls
            # Exact numeric sorting must preserve int64 distinctions above 2**53.
            app.fill(
                app.watches,
                [
                    {"label": "high", "address": "0x1", "type": "int64", "value": 9007199254740993},
                    {"label": "low", "address": "0x2", "type": "int64", "value": 9007199254740992},
                ],
            )
            app.sort_table(app.watches, "value")
            assert app.watches.item(app.watches.get_children()[0], "values")[0] == "low"
            # Invalid UI input is inline and does not break the event pump.
            app.start.set("not an address")
            app.search(False)
            assert "hexadecimal" in app.banner_text.cget("text")
            app.banner.grid_remove()
            for page in app.pages:
                app.navigate(page)
                app.root.update()
                assert app.page_title.cget("text")
            scale = app.display_scale
            app.root.geometry(f"{round(900 * scale)}x{round(620 * scale)}")
            app.root.update()
            app.navigate("search")
            app.root.update()
            canvas = app.page_canvases["search"]
            assert canvas.bbox("all")[3] >= canvas.winfo_height(), (
                "Compact content must remain scrollable"
            )
            print(
                "PASS: clean product UI, attachment, typed searches, watches, comparisons, exact integer sorting, MCP-state sync, background reads, responsive layout and shutdown"
            )
        finally:
            app.close()
            deadline = time.monotonic() + 10
            while not app.closed and time.monotonic() < deadline:
                app.root.update()
                time.sleep(0.01)
            assert app.closed, "Shutdown timed out"


if __name__ == "__main__":
    main()
