import asyncio
import ctypes
import json
import math
import sys
import tempfile
import threading
import unittest
from multiprocessing.connection import Client
from pathlib import Path
from unittest.mock import patch

from backend import Session, start_bridge
from memory import k, pack
from test_support import HarnessSession


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.s = HarnessSession()
        self.info = self.s.call("sample")

    def tearDown(self):
        self.s.close()

    def test_search_refine_watches_snapshots(self):
        i, s = self.info, self.s
        for kind, value, field in [
            ("int32", "137", "health"),
            ("uint32", "42", "coins"),
            ("float32", "3.5", "speed"),
        ]:
            r = s.call("scan", kind=kind, value=value, start=i["start"], end=i["end"])
            self.assertTrue(r["stats"]["complete"])
            self.assertIn(hex(i[field]), [x["address"] for x in r["results"]])
        s.call("scan", kind="int32", value="137", start=i["start"], end=i["end"])
        s.call("watch", address=hex(i["health"]), kind="int32", label="health")
        s.call("snapshot", name="before")
        self.assertEqual(s.call("sample_change", command="damage")["health"], 130)
        self.assertEqual(s.call("refine", value="130")["matches"], 1)
        self.assertEqual(s.call("watches")[0]["value"], 130)
        self.assertEqual(s.call("compare", name="before")[0]["before"], 137)
        self.assertEqual(s.call("compare", name="before")[0]["after"], 130)
        self.assertEqual(s.call("refine", value="137")["matches"], 0)
        with self.assertRaises(OSError):
            s.call("watch", address="0", kind="int32")
        s.call("attach", pid=i["pid"])
        self.assertEqual(s.call("watches"), [])
        self.assertEqual(s.snapshots, {})

    def test_bounds_and_lifecycle(self):
        with self.assertRaises(ValueError):
            self.s.call("scan", kind="int32", value="1", start=10, end=1)
        with self.assertRaises(ValueError):
            pack("bad", "1")
        hits, stats = self.s.process.search(
            "int32", "137", self.info["start"], self.info["end"], budget=4
        )
        self.assertFalse(stats["complete"])
        self.assertEqual(stats["reason"], "byte budget")
        self.s.sample.terminate()
        self.s.sample.wait()
        self.assertEqual(k.WaitForSingleObject(self.s.process.handle, 2000), 0)
        with self.assertRaises(RuntimeError):
            self.s.require()

    def test_comparative_refinement_advances_baseline(self):
        s, i = self.s, self.info
        s.call("scan", kind="int32", value="137", start=i["start"], end=i["end"])
        self.assertEqual(s.call("refine", mode="unchanged")["matches"], 1)
        s.call("sample_change", command="damage")
        self.assertEqual(s.call("refine", mode="decreased")["matches"], 1)
        self.assertEqual(s.call("refine", mode="unchanged")["matches"], 1)
        s.call("sample_change", command="reset")
        self.assertEqual(s.call("refine", mode="increased")["matches"], 1)
        with self.assertRaises(ValueError):
            s.call("refine", mode="invalid")
        s.call("sample_change", command="damage")
        self.assertEqual(s.call("refine", mode="changed")["matches"], 1)
        self.assertEqual(s.call("refine", mode="changed")["matches"], 0)

    def test_cancelled_refinement_preserves_baseline(self):
        s, i = self.s, self.info
        s.call("scan", kind="int32", value="137", start=i["start"], end=i["end"])
        before = dict(s.baseline)
        original = s.process.read

        def cancel_during_read(address, size):
            s.call("cancel_scan")
            return original(address, size)

        with patch.object(s.process, "read", side_effect=cancel_during_read):
            result = s.call("refine", mode="unchanged")
        self.assertTrue(result["preserved_previous"])
        self.assertEqual(result["stats"]["reason"], "cancelled")
        self.assertEqual(s.baseline, before)
        self.assertEqual(s.hits, [i["health"]])

    def test_single_instance_lock_releases(self):
        from instance import InstanceLock

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "session.lock"
            first = InstanceLock(path)
            try:
                with self.assertRaises(RuntimeError):
                    InstanceLock(path)
            finally:
                first.close()
            second = InstanceLock(path)
            second.close()

    def test_failed_query_preserves_prior_candidates(self):
        s, i = self.s, self.info
        s.call("scan", kind="int32", value="137", start=i["start"], end=i["end"])
        previous = dict(s.baseline)

        def failed(*args):
            ctypes.set_last_error(5)
            return 0

        with patch("memory.k.VirtualQueryEx", side_effect=failed):
            with self.assertRaises(OSError):
                s.call("scan", kind="uint32", value="42", start=i["start"], end=i["end"])
        self.assertEqual(s.baseline, previous)
        self.assertEqual(s.kind, "int32")
        self.assertFalse(s.progress["active"])
        self.assertEqual(s.audit[-1]["outcome"], "failed")

    def test_page_fallback_keeps_readable_neighbours(self):
        def read(address, size):
            if size > 4096 or address == 0x2000:
                raise OSError("Test inaccessible page")
            return pack("int32", "137") + bytes(size - 4)

        with (
            patch.object(self.s.process, "regions", return_value=iter([(0x1000, 12288)])),
            patch.object(self.s.process, "read", side_effect=read),
        ):
            hits, stats = self.s.process.search("int32", "137", 0x1000, 0x4000)
        self.assertEqual(hits, [0x1000, 0x3000])
        self.assertEqual(stats["skipped_bytes"], 4096)
        self.assertFalse(stats["complete"])

    def test_watch_capacity_types_removed_and_export_copy(self):
        s, i = self.s, self.info
        address = hex(i["health"])
        s.call("watch", address=address, kind="int32", label="health")
        s.call("snapshot", name="base")
        s.call("watch", address=address, kind="uint32", label="health")
        self.assertEqual(s.call("compare", name="base")[0]["state"], "type changed")
        data = s.call("export")
        data["snapshots"]["base"]["values"][0]["value"] = 0
        self.assertEqual(s.snapshots["base"]["values"][0]["value"], 137)
        s.call("unwatch", address=address.upper())
        self.assertEqual(s.call("compare", name="base")[0]["state"], "removed")
        with self.assertRaises(ValueError):
            s.call("snapshot", name="empty")
        s.watches = {hex(i["start"] + 4 * n): {"label": "v", "type": "int32"} for n in range(256)}
        s.call("watch", address=address, kind="int32", label="updated")
        with self.assertRaises(ValueError):
            s.call("watch", address=hex(i["start"] + 2048), kind="int32")

    def test_strict_json_and_numeric_validation(self):
        from serialization import dumps

        data = json.loads(
            dumps({"values": [math.nan, math.inf, -math.inf]}),
            parse_constant=lambda v: (_ for _ in ()).throw(AssertionError(v)),
        )
        self.assertEqual(data["values"], ["nan", "inf", "-inf"])
        for kind, value in [
            ("int32", "2147483648"),
            ("uint32", "-1"),
            ("float32", "nan"),
            ("float64", "inf"),
        ]:
            with self.subTest(kind=kind, value=value):
                with self.assertRaises(ValueError):
                    pack(kind, value)

    def test_failed_attach_keeps_session_and_closed_session_rejects_work(self):
        old = self.s.process
        with patch("backend.Process", side_effect=PermissionError("Test denied")):
            with self.assertRaises(PermissionError):
                self.s.call("attach", pid=123)
        self.assertIs(self.s.process, old)
        self.assertTrue(self.s.call("status")["alive"])
        self.s.close()
        with self.assertRaises(RuntimeError):
            self.s.call("status")

    def test_detach_and_delete_snapshot(self):
        s, i = self.s, self.info
        s.call("watch", address=hex(i["health"]), kind="int32")
        s.call("snapshot", name="baseline")
        self.assertEqual(s.call("delete_snapshot", name="baseline"), {"deleted": "baseline"})
        self.assertEqual(s.snapshots, {})
        with self.assertRaises(ValueError):
            s.call("compare", name="baseline")
        old = s.process
        s.call("detach")
        self.assertIsNone(old.handle)
        self.assertIsNone(s.call("status")["pid"])
        self.assertEqual(s.call("watches"), [])

    def test_product_has_no_sample_operations(self):
        product = Session()
        try:
            self.assertFalse(hasattr(product, "do_sample"))
            self.assertNotIn("sample", product.call("status"))
        finally:
            product.close()

    def test_shutdown_rejects_queued_mutations(self):
        self.s.begin_close()
        self.assertTrue(self.s.cancel.is_set())
        with self.assertRaises(RuntimeError):
            self.s.call("watch", address=hex(self.info["health"]), kind="int32")

    def test_atomic_export_failure_keeps_original_and_cleans_temporary(self):
        from storage import write_json

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "session.json"
            path.write_text("original", encoding="utf-8")
            unrelated = Path(folder) / "session.json.tmp"
            unrelated.write_text("unrelated", encoding="utf-8")
            with patch.object(
                Path, "replace", side_effect=PermissionError("Test replacement failure")
            ):
                with self.assertRaises(PermissionError):
                    write_json(path, {"value": 42})
            self.assertEqual(path.read_text(), "original")
            self.assertEqual(unrelated.read_text(), "unrelated")
            self.assertEqual(len(list(Path(folder).iterdir())), 2)
            write_json(path, {"value": 42})
            self.assertEqual(json.loads(path.read_text()), {"value": 42})

    def test_bridge_cancellation_preserves_previous_candidates(self):
        s, i = self.s, self.info
        s.call("scan", kind="int32", value="137", start=i["start"], end=i["end"])
        previous_hits, previous_baseline = list(s.hits), dict(s.baseline)
        with tempfile.TemporaryDirectory() as folder:
            config_path = Path(folder) / "session.json"
            listener = start_bridge(s, config_path)
            config = json.loads(config_path.read_text())

            def rpc(action, **args):
                with Client(
                    config["pipe"], family="AF_PIPE", authkey=bytes.fromhex(config["key"])
                ) as c:
                    c.send_bytes(json.dumps({"action": action, "args": args}).encode())
                    self.assertTrue(c.poll(10), "Bridge request timed out")
                    return json.loads(c.recv_bytes())

            entered, release = threading.Event(), threading.Event()
            original = s.process.read

            def slow_read(address, size):
                entered.set()
                if not release.wait(10):
                    raise TimeoutError("Test read gate timed out")
                return original(address, size)

            result = {}
            try:
                with patch.object(s.process, "read", side_effect=slow_read):
                    thread = threading.Thread(
                        target=lambda: result.update(
                            rpc("scan", kind="uint32", value="42", start=i["start"], end=i["end"])
                        )
                    )
                    thread.start()
                    try:
                        self.assertTrue(entered.wait(5))
                        self.assertTrue(rpc("scan_progress")["result"]["active"])
                        self.assertTrue(rpc("cancel_scan")["result"]["requested"])
                    finally:
                        release.set()
                        thread.join(10)
                    self.assertFalse(thread.is_alive())
                self.assertEqual(result["result"]["stats"]["reason"], "cancelled")
                self.assertTrue(result["result"]["preserved_previous"])
                self.assertEqual(s.kind, "int32")
                self.assertEqual(s.hits, previous_hits)
                self.assertEqual(s.baseline, previous_baseline)
            finally:
                release.set()
                listener.close()

    def test_real_mcp_stdio_roundtrip(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        temp = tempfile.TemporaryDirectory()
        config = Path(temp.name) / "test-session.json"
        listener = start_bridge(self.s, config)

        async def exercise():
            params = StdioServerParameters(
                command=sys.executable,
                args=[str(Path(__file__).with_name("mcp_server.py"))],
                env={"CHEATCRAFT_SESSION_FILE": str(config)},
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    names = {t.name for t in (await client.list_tools()).tools}
                    self.assertEqual(len(names), 10)
                    self.assertNotIn("attach", names)
                    r = await client.call_tool("scan_progress", {})
                    self.assertFalse(r.isError)
                    r = await client.call_tool("cancel_scan", {})
                    self.assertFalse(r.isError)
                    r = await client.call_tool("session_status", {})
                    self.assertFalse(r.isError)
                    self.assertEqual(json.loads(r.content[0].text)["pid"], self.info["pid"])
                    r = await client.call_tool(
                        "search_memory",
                        {
                            "kind": "int32",
                            "value": "137",
                            "start": self.info["start"],
                            "end": self.info["end"],
                        },
                    )
                    self.assertFalse(r.isError)
                    self.assertEqual(json.loads(r.content[0].text)["matches"], 1)
                    r = await client.call_tool("refine_memory", {"mode": "unchanged"})
                    self.assertFalse(r.isError)
                    self.assertEqual(json.loads(r.content[0].text)["matches"], 1)
                    r = await client.call_tool(
                        "add_watch", {"address": hex(self.info["health"]), "kind": "int32"}
                    )
                    self.assertFalse(r.isError)
                    r = await client.call_tool("capture_snapshot", {"name": "mcp"})
                    self.assertFalse(r.isError)
                    self.s.call("sample_change", command="damage")
                    r = await client.call_tool("compare_snapshot", {"name": "mcp"})
                    self.assertFalse(r.isError)
                    self.assertIn("130", r.content[0].text)
                    r = await client.call_tool("search_memory", {"kind": "bad", "value": "1"})
                    self.assertTrue(r.isError)

        try:
            asyncio.run(exercise())
        finally:
            listener.close()
            temp.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
