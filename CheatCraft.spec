# PyInstaller multi-executable portable folder. Build on Windows x64.
from pathlib import Path

root = Path(SPECPATH)
common = dict(pathex=[str(root)], hiddenimports=[], hookspath=[], runtime_hooks=[],
              excludes=['test_support', 'test_cheatcraft', 'test_ui', 'sample'], noarchive=False)
desktop = Analysis([str(root/'app.py')], **common)
desktop_pyz = PYZ(desktop.pure)
desktop_exe = EXE(desktop_pyz, desktop.scripts, [], exclude_binaries=True, name='CheatCraft',
                  debug=False, strip=False, upx=False, console=False)
server = Analysis([str(root/'mcp_server.py')], **common)
server_pyz = PYZ(server.pure)
server_exe = EXE(server_pyz, server.scripts, [], exclude_binaries=True, name='CheatCraft-MCP',
                 debug=False, strip=False, upx=False, console=True)
COLLECT(desktop_exe, server_exe, desktop.binaries, desktop.datas, server.binaries, server.datas,
        strip=False, upx=False, name='CheatCraft')
