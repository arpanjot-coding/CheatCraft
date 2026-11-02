"""Owned-process fixtures. This module is never imported by the product."""

import json
import subprocess
import sys

from backend import HOME, Session


class HarnessSession(Session):
    def __init__(self):
        super().__init__()
        self.sample = None
        self.sample_info = None

    def do_sample(self):
        if self.sample and self.sample.poll() is None:
            self.do_attach(self.sample_info["pid"])
            return self.sample_info
        if self.sample:
            self.sample.stdin.close()
            self.sample.stdout.close()
        self.sample = subprocess.Popen(
            [sys.executable, str(HOME / "sample.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            creationflags=0x08000000,
        )
        self.sample_info = json.loads(self.sample.stdout.readline())
        self.do_attach(self.sample_info["pid"])
        return self.sample_info

    def do_sample_change(self, command):
        if command not in {"damage", "reset"} or not self.sample or self.sample.poll() is not None:
            raise ValueError("The controlled target is not running.")
        self.sample.stdin.write(command + "\n")
        self.sample.stdin.flush()
        return json.loads(self.sample.stdout.readline())

    def close(self):
        super().close()
        if self.sample and self.sample.poll() is None:
            self.sample.terminate()
            self.sample.wait(timeout=5)
        if self.sample:
            self.sample.stdin.close()
            self.sample.stdout.close()
