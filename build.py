"""
Build script: package Personal AI as a single Windows executable.

Usage:
    pip install pyinstaller
    python build.py

Output:
    dist/PersonalAI.exe  (~150-250MB)
"""
import os, sys, shutil
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
SPEC_FILE = ROOT / "personal-ai.spec"
STATIC_DIR = ROOT / "proxy" / "static"

# --- PyInstaller spec-like configuration ---

EXE_NAME = "PersonalAI"
ENTRY_POINT = "run.py"

# Data files to bundle with the executable
DATAS = [
    (str(STATIC_DIR), "proxy/static"),
]

# Hidden imports (modules PyInstaller may miss)
HIDDEN_IMPORTS = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "chromadb",
    "sentence_transformers",
]

# --- Write spec file ---

spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['{ENTRY_POINT}'],
    pathex=[],
    binaries=[],
    datas={DATAS},
    hiddenimports={HIDDEN_IMPORTS},
    hookspath=[],
    hooksconfig={{}},
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
    name='{EXE_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # Show console for server logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""

with open(SPEC_FILE, "w", encoding="utf-8") as f:
    f.write(spec_content)

print(f"✓ Spec file written: {SPEC_FILE}")
print()
print("=" * 50)
print("How to build:")
print("=" * 50)
print()
print("1. Install dependencies:")
print("   pip install pyinstaller")
print("   pip install -r requirements.txt")
print()
print("2. Build:")
print("   pyinstaller personal-ai.spec")
print()
print("3. Output:")
print(f"   {DIST / EXE_NAME}.exe")
print()
print("4. Distribute:")
print(f"   Share {DIST / EXE_NAME}.exe — it includes everything.")
print("   First-time startup may trigger Windows Defender — click 'More info' → 'Run anyway'.")
print()
print("Note: Built EXE is ~150-250MB due to embedded Python + ChromaDB.")
