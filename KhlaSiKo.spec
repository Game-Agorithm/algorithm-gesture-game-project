# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


project_root = Path(SPECPATH).resolve()

cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all("cv2")
mediapipe_datas, mediapipe_binaries, mediapipe_hiddenimports = collect_all("mediapipe")
pygame_datas, pygame_binaries, pygame_hiddenimports = collect_all("pygame")
customtkinter_datas, customtkinter_binaries, customtkinter_hiddenimports = collect_all(
    "customtkinter"
)

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[
        *cv2_binaries,
        *mediapipe_binaries,
        *pygame_binaries,
        *customtkinter_binaries,
    ],
    datas=[
        (str(project_root / "assets"), "assets"),
        *cv2_datas,
        *mediapipe_datas,
        *pygame_datas,
        *customtkinter_datas,
    ],
    hiddenimports=[
        *cv2_hiddenimports,
        *mediapipe_hiddenimports,
        *pygame_hiddenimports,
        *customtkinter_hiddenimports,
        "src.audio_manager",
        "src.camera",
        "src.config",
        "src.game_rules",
        "src.game_state",
        "src.gesture_recognizer",
        "src.hand_tracker",
        "src.renderer",
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
    [],
    exclude_binaries=True,
    name="KhlaSiKo",
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

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="KhlaSiKo",
)
