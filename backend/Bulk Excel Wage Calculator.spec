# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files


# ---------------------------------------------------------
# Hidden imports
# ---------------------------------------------------------

hiddenimports = collect_submodules(
    "modules.PrevailingWageCalculator"
)


# ---------------------------------------------------------
# Package data
# ---------------------------------------------------------

datas = collect_data_files(
    "modules.PrevailingWageCalculator",
    include_py_files=False
)


# ---------------------------------------------------------
# Explicitly include city database
# ---------------------------------------------------------

datas += [
    (
        "modules/PrevailingWageCalculator/data/us_cities.db",
        "data"
    )
]


# ---------------------------------------------------------
# Analysis
# ---------------------------------------------------------

a = Analysis(
    ['modules/PrevailingWageCalculator/bulk_launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)


# ---------------------------------------------------------
# Python archive
# ---------------------------------------------------------

pyz = PYZ(
    a.pure,
    a.zipped_data,
)


# ---------------------------------------------------------
# EXE
# ---------------------------------------------------------

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Bulk Excel Wage Calculator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)