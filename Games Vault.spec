# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['G:/Games_Vault/Games_Vault/Games Vault.py'],
    pathex=[],
    binaries=[],
    datas=[('G:/Games_Vault/Games_Vault/layout', 'layout/'), ('G:/Games_Vault/Games_Vault/resources', 'resources/'), ('G:/Games_Vault/Games_Vault/database.py', '.'), ('G:/Games_Vault/Games_Vault/desktop_widget.py', '.'), ('G:/Games_Vault/Games_Vault/Epic.py', '.'), ('G:/Games_Vault/Games_Vault/Logging.py', '.'), ('G:/Games_Vault/Games_Vault/resources.qrc', '.'), ('G:/Games_Vault/Games_Vault/Steam.py', '.')],
    hiddenimports=[],
    hookspath=[],
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
    [],
    exclude_binaries=True,
    name='Games Vault',
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
    icon=['G:\\Games_Vault\\Games_Vault\\resources\\icons\\app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Games Vault',
)
