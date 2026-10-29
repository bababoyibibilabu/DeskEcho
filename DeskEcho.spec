# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas_chroma, binaries_chroma, hiddenimports_chroma = collect_all('chromadb')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries_chroma,
    datas=datas_chroma,
    hiddenimports=hiddenimports_chroma + ['chromadb.telemetry.product.posthog', 'posthog'],
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DeskEcho',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
