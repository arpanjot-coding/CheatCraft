"""Reproduce the installed third-party licence inventory without network access."""

import importlib.metadata as md
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
parts = [
    "CheatCraft dependency notices\nGenerated from installed distributions. Preserve these notices when redistributing dependencies.\n"
]
for dist in sorted(md.distributions(), key=lambda d: d.metadata["Name"].lower()):
    if dist.metadata["Name"].lower() == "pip":
        continue
    meta = dist.metadata
    parts.append("\n" + "=" * 78 + "\n" + meta["Name"] + " " + dist.version + "\n")
    parts.append(
        "Declared licence: "
        + str(meta.get("License-Expression") or meta.get("License") or "See licence files below")
        + "\n"
    )
    for f in dist.files or []:
        if any(
            term in f.name.lower() for term in ("license", "licence", "copying", "notice")
        ) and ".dist-info" in str(f):
            path = dist.locate_file(f)
            if path.is_file():
                parts.append(
                    "\n--- "
                    + str(f)
                    + " ---\n"
                    + path.read_text(encoding="utf-8", errors="replace")
                    + "\n"
                )
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.exists():
    parts.append("\nPython bundled runtime notices\n" + python_license.read_text(encoding="utf-8"))
(root / "THIRD_PARTY_NOTICES.txt").write_text("".join(parts), encoding="utf-8")
print("Wrote THIRD_PARTY_NOTICES.txt")
