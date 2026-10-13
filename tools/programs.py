import os,subprocess
_PROCESSES={}
def open_path(path): os.startfile(path); return {"success":True,"path":path}
def run_program(program,args=None,working_directory=None):
    argv=[program]+(args or []); p=subprocess.Popen(argv,cwd=working_directory or None); _PROCESSES[p.pid]=p; return {"success":True,"pid":p.pid,"program":program,"args":args or []}
def stop_program(pid):
    p=_PROCESSES.get(int(pid))
    if p: p.terminate(); return {"success":True,"pid":int(pid)}
    try:
        import psutil; psutil.Process(int(pid)).terminate(); return {"success":True,"pid":int(pid)}
    except Exception as exc: return {"success":False,"error":str(exc),"pid":int(pid)}
def list_programs(limit=100):
    import psutil
    return {"success":True,"processes":[{"pid":p.info["pid"],"name":p.info["name"]} for p in list(psutil.process_iter(["pid","name"]))[:limit]]}
