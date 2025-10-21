# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for minimal SACMES Agent
# This creates the smallest possible EXE by excluding unnecessary modules

block_cipher = None

# Minimal analysis - only include what's absolutely necessary
a = Analysis(
    ['agent.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'socketio',
        'engineio',
        'websocket',
        'requests',
        'urllib3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude everything we don't need (but keep urllib - it's required by engineio)
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'IPython',
        'notebook',
        'pytest',
        'setuptools',
        'lib2to3',
        'pydoc_data',
        'pdb',
        'profile',
        'pstats',
        'turtle',
        'doctest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove unnecessary files
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SACMES_Agent_Minimal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip debug symbols
    upx=False,   # Don't use UPX compression (can cause issues)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI only)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Netzlab.ico',
)
