"""Read-only Windows process memory primitives. No debug privilege or write handles."""

import ctypes as C
import math
import struct
import time
from ctypes import wintypes as W

import psutil

TYPES = {"int32": "i", "uint32": "I", "int64": "q", "float32": "f", "float64": "d"}
k = C.WinDLL("kernel32", use_last_error=True)
k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
k.OpenProcess.restype = W.HANDLE
k.CloseHandle.argtypes = [W.HANDLE]
k.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
k.WaitForSingleObject.restype = W.DWORD
k.ReadProcessMemory.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
k.ReadProcessMemory.restype = W.BOOL


class MBI(C.Structure):
    _fields_ = [
        ("BaseAddress", C.c_void_p),
        ("AllocationBase", C.c_void_p),
        ("AllocationProtect", W.DWORD),
        ("PartitionId", W.WORD),
        ("RegionSize", C.c_size_t),
        ("State", W.DWORD),
        ("Protect", W.DWORD),
        ("Type", W.DWORD),
    ]


k.VirtualQueryEx.argtypes = [W.HANDLE, C.c_void_p, C.POINTER(MBI), C.c_size_t]
k.VirtualQueryEx.restype = C.c_size_t


def processes():
    return sorted(
        [p.info for p in psutil.process_iter(["pid", "name"])],
        key=lambda p: (p["name"] or "").lower(),
    )


def pack(kind, value):
    if kind not in TYPES:
        raise ValueError("Unsupported value type: " + str(kind))
    try:
        number = float(value) if kind.startswith("float") else int(value)
        if isinstance(number, float) and not math.isfinite(number):
            raise ValueError("A finite number is required.")
        return struct.pack("<" + TYPES[kind], number)
    except (ValueError, OverflowError, struct.error) as e:
        raise ValueError(f"Enter a valid {kind} value within its numeric range.") from e


def unpack(kind, data):
    return struct.unpack("<" + TYPES[kind], data)[0]


class Process:
    def __init__(self, pid):
        if C.sizeof(C.c_void_p) != 8:
            raise RuntimeError("Use 64-bit Python.")
        self.pid = int(pid)
        self.created = psutil.Process(pid).create_time()
        self.handle = k.OpenProcess(0x100410, False, pid)
        if not self.handle:
            code = C.get_last_error()
            if code == 5:
                raise PermissionError(
                    5,
                    f"Windows denied read access to PID {pid}. The target may use different privileges, restricted permissions, or process protection. This error alone does not identify anti-cheat. Run CheatCraft and your development process under the same account and privilege level. Protected third-party games are unsupported.",
                )
            raise C.WinError(code)

    def close(self):
        if self.handle:
            k.CloseHandle(self.handle)
            self.handle = None

    def alive(self):
        if not self.handle or k.WaitForSingleObject(self.handle, 0) != 258:
            raise RuntimeError("Target exited. Attach again.")

    def read(self, address, size):
        self.alive()
        buf = C.create_string_buffer(size)
        count = C.c_size_t()
        if (
            not k.ReadProcessMemory(self.handle, address, buf, size, C.byref(count))
            or count.value != size
        ):
            raise OSError("Memory is no longer readable at " + hex(address))
        return buf.raw

    def value(self, address, kind):
        if kind not in TYPES:
            raise ValueError("Unsupported value type: " + str(kind))
        if address < 0 or address >= 0x7FFFFFFF0000:
            raise ValueError("Address is outside the supported application address space.")
        return unpack(kind, self.read(address, struct.calcsize(TYPES[kind])))

    def regions(self, start=0, end=0x7FFFFFFF0000):
        self.alive()
        address = start
        while address < end:
            mbi = MBI()
            if not k.VirtualQueryEx(self.handle, address, C.byref(mbi), C.sizeof(mbi)):
                code = C.get_last_error()
                self.alive()
                if code == 87:  # Above the target's highest accessible address (including WOW64).
                    return
                raise OSError(
                    code, f"Cannot enumerate memory at {hex(address)}; the scan did not finish."
                )
            base, size = mbi.BaseAddress or 0, mbi.RegionSize
            if size <= 0 or base + size <= address:
                raise OSError(
                    "Windows returned an invalid memory-region size; the scan did not finish."
                )
            if mbi.State == 0x1000 and not mbi.Protect & (0x100 | 0x01) and mbi.Protect & 0xEE:
                yield max(base, start), min(base + size, end) - max(base, start)
            address = base + size

    def search(
        self,
        kind,
        value,
        start=0,
        end=0x7FFFFFFF0000,
        budget=256 * 1024 * 1024,
        cap=10000,
        cancel=None,
        progress=None,
        observed=None,
    ):
        needle = pack(kind, value)
        hits, scanned, skipped = [], 0, 0
        started = time.monotonic()

        def stats(reason):
            return {
                "bytes": scanned,
                "skipped_bytes": skipped,
                "complete": reason == "finished" and skipped == 0,
                "reason": reason,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }

        for base, size in self.regions(start, end):
            offset = 0
            while offset < size:
                if cancel is not None and cancel.is_set():
                    return hits, stats("cancelled")
                if scanned >= budget:
                    return hits, stats("byte budget")
                n = min(1024 * 1024, size - offset, budget - scanned)
                address = base + offset
                try:
                    data = self.read(address, min(n + len(needle) - 1, size - offset))
                    blocks = [(address, data, n)]
                except OSError:
                    # A decommitted/protected page must not hide readable neighbours.
                    blocks = []
                    cursor = address
                    while cursor < address + n:
                        if cancel is not None and cancel.is_set():
                            return hits, stats("cancelled")
                        length = min(4096 - cursor % 4096, address + n - cursor)
                        read_length = min(
                            length + len(needle) - 1, 4096 - cursor % 4096, base + size - cursor
                        )
                        try:
                            blocks.append((cursor, self.read(cursor, read_length), length))
                        except OSError:
                            skipped += length
                        cursor += length
                for block_address, data, limit in blocks:
                    pos = data.find(needle)
                    while pos >= 0 and pos < limit:
                        if (block_address + pos) % len(needle) == 0:
                            hits.append(block_address + pos)
                            if observed is not None:
                                observed[block_address + pos] = data[pos : pos + len(needle)]
                            if len(hits) >= cap:
                                scanned += n
                                return hits, stats("result cap")
                        pos = data.find(needle, pos + 1)
                scanned += n
                offset += n
                if progress is not None:
                    progress({**stats("scanning"), "matches": len(hits), "address": hex(address)})
        return hits, stats("cancelled" if cancel is not None and cancel.is_set() else "finished")
