# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas_chroma, binaries_chroma, hiddenimports_chroma = collect_all('chromadb')
datas_sherpa, binaries_sherpa, hiddenimports_sherpa = collect_all('sherpa_onnx')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries_chroma + binaries_sherpa,
    datas=datas_chroma + datas_sherpa + [('assets', 'assets')],
    hiddenimports=hiddenimports_chroma + hiddenimports_sherpa + ['chromadb.telemetry.product.posthog', 'posthog', 'soundfile'],
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
    icon='assets/flower_logo.ico',
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
