import subprocess

def wifi_info():
    try:
        p = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        lines = [line.strip() for line in p.stdout.splitlines() if line.strip()]
        return {"ok": p.returncode == 0, "text": "\n".join(lines), "returncode": p.returncode}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
