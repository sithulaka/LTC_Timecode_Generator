# -*- mode: python ; coding: utf-8 -*-

import eel as _eel
import os as _os

_eel_dir = _os.path.dirname(_eel.__file__)

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('web', 'web'),
        (_eel_dir, 'eel'),
    ],
    hiddenimports=[
        'bottle_websocket',
        'gevent',
        'gevent.signal',
        'gevent.threading',
        'gevent.event',
        'gevent.queue',
        'gevent._semaphore',
        'gevent.local',
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
    name='LTC_Timecode_Generator',
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
