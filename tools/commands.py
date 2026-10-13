import subprocess
import threading
import time

class CommandTools:
    def __init__(self):
        self._lock=threading.Lock()
        self._active=set()

    def run_command(self,command,shell="powershell",timeout=None):
        exe="powershell.exe" if shell.lower().startswith("power") else "cmd.exe"
        args=[exe,"-NoProfile","-Command",command] if exe.startswith("power") else [exe,"/c",command]
        p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",errors="replace")
        with self._lock:
            self._active.add(p)
        started=time.monotonic()
        try:
            while p.poll() is None:
                if timeout is not None and time.monotonic()-started >= timeout:
                    self._terminate(p)
                    stdout,stderr=p.communicate()
                    return {"success":False,"stdout":stdout,"stderr":stderr,"exit_code":p.returncode,"timed_out":True}
                time.sleep(0.1)
            stdout,stderr=p.communicate()
            return {"success":p.returncode==0,"stdout":stdout,"stderr":stderr,"exit_code":p.returncode}
        finally:
            with self._lock:
                self._active.discard(p)

    @staticmethod
    def _terminate(process):
        if process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=1)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    def cancel_all(self):
        with self._lock:
            active=list(self._active)
        for process in active:
            self._terminate(process)
        return {"success":True,"cancelled":len(active)}
