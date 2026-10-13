from pathlib import Path
ROOT=Path(__file__).resolve().parent
for name in ("data/settings","data/sessions","data/history","workspace","screenshots","logs","temp","assets/icons","assets/backgrounds","assets/sounds"): (ROOT/name).mkdir(parents=True,exist_ok=True)
try:
    from agent import main
except Exception as exc:
    # windowed builds have no console; leave a recoverable diagnostic beside the exe.
    try:
        (ROOT / "startup_error.txt").write_text(
            f"{type(exc).__name__}: {exc}\n",
            encoding="utf-8",
        )
    except Exception:
        pass
    raise SystemExit(f"本地 Agent 启动失败：{exc}\n请先运行 install.ps1")
if __name__=="__main__": raise SystemExit(main())
