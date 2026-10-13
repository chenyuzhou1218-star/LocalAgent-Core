import os,platform,shutil,socket,subprocess

try:
    import psutil
except Exception:
    psutil=None

def system_info():
    disk=shutil.disk_usage(os.getcwd())
    data={
        "success":True,
        "windows":platform.platform(),
        "windows_version":platform.version(),
        "machine":platform.machine(),
        "processor":platform.processor() or platform.uname().processor,
        "cpu_logical_cores":os.cpu_count(),
        "user":os.environ.get("USERNAME",""),
        "hostname":socket.gethostname(),
        "cwd":os.getcwd(),
        "disk_total_bytes":disk.total,
        "disk_free_bytes":disk.free,
        "disk_used_bytes":disk.used,
    }
    if psutil:
        memory=psutil.virtual_memory()
        data["memory_total_bytes"]=memory.total
        data["memory_available_bytes"]=memory.available
        data["memory_used_percent"]=memory.percent
        data["cpu_usage_percent"]=psutil.cpu_percent(interval=0.15)
    try:
        result=subprocess.run(["powershell.exe","-NoProfile","-Command","Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=4)
        data["gpu"]=[line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        data["gpu"]=[]
    return data
