"""Resolve zipped Tcl/Tk libraries in Python 3.14 Windows virtual environments."""

import os
import sys
import zipfile
from pathlib import Path


def prepare():
    if getattr(sys, "frozen", False):
        return  # PyInstaller's tkinter runtime hook configures its bundled libraries.
    source = Path(sys.base_prefix) / "tcl"
    target = Path(__file__).resolve().parent / ".tk-runtime"
    for prefix, folder, env in [
        ("libtcl", "tcl_library", "TCL_LIBRARY"),
        ("libtk", "tk_library", "TK_LIBRARY"),
    ]:
        archives = sorted(source.glob(prefix + "*.zip"))
        if archives and env not in os.environ:
            marker = target / folder / ("init.tcl" if prefix == "libtcl" else "tk.tcl")
            if not marker.exists():
                with zipfile.ZipFile(archives[-1]) as archive:
                    archive.extractall(target)
            os.environ[env] = str(target / folder)
