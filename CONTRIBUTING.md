# Contributing

CheatCraft is an early Windows diagnostic tool. Small changes with reproducible evidence are welcome.

## Development setup

Use Windows x64 and Python 3.14. Create a virtual environment, then install `requirements-dev.txt`. Runtime dependencies are pinned separately in `requirements-lock.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
.\.venv\Scripts\python -m unittest -v test_cheatcraft
.\.venv\Scripts\python test_ui.py
```

The controlled target is test infrastructure and is not imported by the application or included in the portable executable. Test session files are isolated from the live desktop.

## Pull requests

Explain the problem, final behavior and relevant validation. Add regression coverage for bugs. Keep target I/O off the Tk event thread. Preserve cancellation and previous-state behavior when scans fail. Request only the process permissions needed for the operation. Avoid logging session secrets or target memory in CI output.

Do not add automatic elevation, driver installation, anti-cheat evasion, network listeners or external telemetry as incidental changes. Changes to access boundaries need an explicit design discussion.

By contributing, you agree that your contribution is provided under the repository's MIT licence. Third-party components retain their own licences and notices.
