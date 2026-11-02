"""Smoke-test the packaged desktop and actual MCP executable against an owned fixture."""

import asyncio
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from backend import start_bridge
from test_support import HarnessSession


async def check_server(executable, config, expected_pid, allocation=None):
    parameters = StdioServerParameters(
        command=str(executable), args=[], env={"CHEATCRAFT_SESSION_FILE": str(config)}
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            tools = await client.list_tools()
            assert len(tools.tools) == 10
            result = await client.call_tool("session_status", {})
            assert not result.isError
            import json

            assert json.loads(result.content[0].text)["pid"] == expected_pid
            if allocation:
                result = await client.call_tool(
                    "search_memory",
                    {
                        "kind": "int32",
                        "value": "137",
                        "start": allocation["start"],
                        "end": allocation["end"],
                    },
                )
                assert not result.isError
                assert json.loads(result.content[0].text)["matches"] == 1


def main():
    package = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory() as folder:
        config = Path(folder) / "fixture.json"
        session = HarnessSession()
        info = session.call("sample")
        listener = start_bridge(session, config)
        try:
            asyncio.run(check_server(package / "CheatCraft-MCP.exe", config, info["pid"], info))
        finally:
            listener.close()
            session.close()
        desktop_config = Path(folder) / "desktop.json"
        env = dict(os.environ, CHEATCRAFT_SESSION_FILE=str(desktop_config))
        desktop = subprocess.Popen([str(package / "CheatCraft.exe")], cwd=folder, env=env)
        try:
            deadline = time.monotonic() + 20
            while (
                not desktop_config.exists()
                and desktop.poll() is None
                and time.monotonic() < deadline
            ):
                time.sleep(0.1)
            assert desktop_config.exists(), "Desktop did not create its local bridge"
            time.sleep(2)
            assert desktop.poll() is None, "Desktop exited during initialization"
            asyncio.run(check_server(package / "CheatCraft-MCP.exe", desktop_config, None))
        finally:
            if desktop.poll() is None:
                desktop.terminate()
            desktop.wait(timeout=10)
    print(
        "PASS: packaged MCP handshake, tool discovery, owned-process memory search, desktop startup and desktop/MCP bridge"
    )


if __name__ == "__main__":
    main()
