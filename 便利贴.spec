# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=['d:\\tarepro\\bianlitie'],
    binaries=[],
    datas=[
        ('ui', 'ui'),
        ('model', 'model'),
        ('tools', 'tools'),
        ('zhang.jpg', '.'),
    ],
    hiddenimports=[
        'PyQt6', 
        'PyQt6.QtWidgets', 
        'PyQt6.QtCore', 
        'PyQt6.QtGui',
        'win32com', 
        'win32com.client', 
        'pythoncom',
        'urllib.request',
        'urllib.parse',
        'json',
        'sqlite3',
        'os',
        'datetime',
        'threading',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='便利贴',
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
    icon='zhang.ico',
)
