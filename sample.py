"""Owned test target: a dedicated native allocation with deterministic state."""

import ctypes as C
import json
import os
import sys

k = C.WinDLL("kernel32", use_last_error=True)
k.VirtualAlloc.argtypes = [C.c_void_p, C.c_size_t, C.c_ulong, C.c_ulong]
k.VirtualAlloc.restype = C.c_void_p
address = k.VirtualAlloc(None, 4096, 0x3000, 0x04)
if not address:
    raise C.WinError(C.get_last_error())
health = C.c_int32.from_address(address)
coins = C.c_uint32.from_address(address + 8)
speed = C.c_float.from_address(address + 16)
health.value, coins.value, speed.value = 137, 42, 3.5
print(
    json.dumps(
        {
            "pid": os.getpid(),
            "start": address,
            "end": address + 4096,
            "health": address,
            "coins": address + 8,
            "speed": address + 16,
        }
    ),
    flush=True,
)
for line in sys.stdin:
    command = line.strip()
    if command == "damage":
        health.value -= 7
    elif command == "reset":
        health.value, coins.value, speed.value = 137, 42, 3.5
    elif command == "quit":
        break
    print(
        json.dumps({"health": health.value, "coins": coins.value, "speed": speed.value}), flush=True
    )
