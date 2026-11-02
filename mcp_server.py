"""Official MCP SDK adapter; communicates with the running desktop session."""

from mcp.server.fastmcp import FastMCP

from backend import remote

mcp = FastMCP(
    "CheatCraft",
    instructions="Read-only diagnostics for the process explicitly attached in the CheatCraft desktop app. Scans are aligned, exact-value and bounded; check completeness stats. No attach or memory-write tools are exposed.",
)


@mcp.tool()
def session_status() -> dict:
    """Inspect the attached process, scan coverage, result count and recent audit events."""
    return remote("status")


@mcp.tool()
def search_memory(kind: str, value: str, start: int = 0, end: int = 0x7FFFFFFF0000) -> dict:
    """Start an exact aligned search (int32, uint32, int64, float32, float64). Replaces prior candidates; max 256 MiB / 10,000 matches. Addresses are decimal integers."""
    return remote("scan", kind=kind, value=value, start=start, end=end)


@mcp.tool()
def refine_memory(value: str = "", mode: str = "equal") -> dict:
    """Refine candidates by equal, changed, unchanged, increased or decreased. Comparisons use the last successful scan's observations; only equal uses value. Successful refinement advances the baseline. Cancellation preserves prior candidates."""
    return remote("refine", value=value, mode=mode)


@mcp.tool()
def scan_progress() -> dict:
    """Read active scan progress without waiting for the scan's session lock."""
    return remote("scan_progress")


@mcp.tool()
def cancel_scan() -> dict:
    """Request cancellation of an active search/refinement; previous candidates are preserved."""
    return remote("cancel_scan")


@mcp.tool()
def add_watch(address: str, kind: str, label: str = "value") -> dict:
    """Watch an address in the attached process; hexadecimal strings accepted."""
    return remote("watch", address=address, kind=kind, label=label)


@mcp.tool()
def list_watches() -> list:
    """Read current watch values, or report inaccessible memory."""
    return remote("watches")


@mcp.tool()
def remove_watch(address: str) -> list:
    """Remove a watch by canonical hexadecimal address."""
    return remote("unwatch", address=address)


@mcp.tool()
def capture_snapshot(name: str) -> dict:
    """Capture current watched values under a name; overwrites same-name snapshot."""
    return remote("snapshot", name=name)


@mcp.tool()
def compare_snapshot(name: str) -> list:
    """Compare a named watch snapshot with live values; reads are not atomic."""
    return remote("compare", name=name)


if __name__ == "__main__":
    from multiprocessing import freeze_support

    freeze_support()
    mcp.run(transport="stdio")
