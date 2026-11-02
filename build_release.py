"""Build and archive the Windows portable package. Run tests before invoking."""

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

from tk_runtime import prepare
from version import VERSION

ROOT = Path(__file__).resolve().parent


def main():
    prepare()  # Make this Python installation's zipped Tcl/Tk visible to build hooks.
    output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "dist"
    output.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PYINSTALLER_CONFIG_DIR"] = str(output / "build-cache")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "--workpath",
            str(output / "build"),
            "--distpath",
            str(output),
            "CheatCraft.spec",
        ],
        cwd=ROOT,
        env=env,
        check=True,
    )
    package = output / "CheatCraft"
    for name in (
        "LICENSE",
        "README.md",
        "CHANGELOG.md",
        "SECURITY.md",
        "THIRD_PARTY_NOTICES.txt",
        "VERIFICATION.txt",
    ):
        shutil.copy2(ROOT / name, package / name)
    shutil.copytree(ROOT / "assets", package / "assets", dirs_exist_ok=True)
    archive = Path(
        shutil.make_archive(
            str(output / f"CheatCraft-v{VERSION}-windows-x64"),
            "zip",
            root_dir=output,
            base_dir="CheatCraft",
        )
    )
    checksum = archive.with_suffix(".sha256")
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    checksum.write_text(digest + "  " + archive.name + "\n", encoding="ascii")
    print(archive)
    print(checksum)


if __name__ == "__main__":
    main()
