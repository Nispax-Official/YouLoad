from pathlib import Path

project_root = Path(SPECPATH).parent
icon_path = project_root / "ui" / "assets" / "youload-icon.ico"

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "ui"), "ui"),
        (str(project_root / "runtime"), "runtime"),
        (str(project_root / "updater" / "components.json"), "updater"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="YouLoad",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(icon_path) if icon_path.exists() else None,
)

COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="YouLoad",
)
