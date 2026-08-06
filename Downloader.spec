# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# Base dir (SPECPATH is defined by PyInstaller at build time)
project_dir = SPECPATH if 'SPECPATH' in globals() else os.path.abspath(os.getcwd())


datas = [
    (os.path.join(project_dir, 'config.json'), '.'),
]

# Include bin directory if present
bin_dir = os.path.join(project_dir, 'bin')
if os.path.exists(bin_dir):
    datas.append((bin_dir, 'bin'))

hiddenimports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'pydantic',
    'yt_dlp',
    'pystray',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'requests',
]

a = Analysis(
    [os.path.join(project_dir, 'desktop', 'app.py')],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', '_tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas',
        'zmq', 'jedi', 'black', 'notebook', 'IPython', 'pygments',
        'lark', 'nbformat', 'blib2to3', 'pytokens', 'cryptography', 'bcrypt'
    ],

    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Downloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Shows console window with server startup banner

    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Downloader',
)
