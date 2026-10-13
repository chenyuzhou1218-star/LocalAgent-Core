import os, sys
from pathlib import Path

if getattr(sys, "frozen", False):
    bundle_dir = Path(sys._MEIPASS)
    dll_dirs = [bundle_dir, bundle_dir / "PySide6", bundle_dir / "shiboken6"]
    existing = os.environ.get("PATH", "")
    os.environ["PATH"] = os.pathsep.join(str(path) for path in dll_dirs if path.exists()) + os.pathsep + existing
    for path in dll_dirs:
        if path.exists():
            try:
                os.add_dll_directory(str(path))
            except Exception:
                pass
