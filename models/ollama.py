from __future__ import annotations
import json, urllib.request, subprocess, http.client, threading, os, time
from pathlib import Path
from urllib.parse import urlparse

class OllamaProvider:
    def __init__(self,base_url="http://127.0.0.1:11434",timeout=None): self.base_url=base_url.rstrip("/"); self.timeout=timeout; self._connection=None; self._lock=threading.Lock()
    def _json(self,path,payload=None,timeout=None):
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None
        req=urllib.request.Request(self.base_url+path,data=data,headers={"Content-Type":"application/json"} if data else {})
        with urllib.request.urlopen(req,timeout=timeout or self.timeout) as r: return json.loads(r.read().decode("utf-8"))
    def ensure_server(self):
        """Start the installed local Ollama service when the desktop app was opened first."""
        if self.is_online(): return True
        candidates=[Path.home()/"AppData/Local/Programs/Ollama/ollama.exe",Path("ollama.exe")]
        exe=next((str(p) for p in candidates if p.exists()),"ollama")
        parsed=urlparse(self.base_url)
        host=parsed.hostname or "127.0.0.1"
        configured_port=parsed.port or 11434
        ports=[]
        for port in (configured_port, 11435):
            if port not in ports: ports.append(port)
        flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
        for port in ports:
            self.base_url=f"http://{host}:{port}"
            env=os.environ.copy()
            env["OLLAMA_HOST"]=f"{host}:{port}"
            try:
                process=subprocess.Popen([exe,"serve"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags,env=env)
            except Exception:
                continue
            for _ in range(120):
                if process.poll() is not None: break
                if self.is_online(): return True
                time.sleep(.5)
            if self.is_online(): return True
            if process.poll() is None:
                try: process.terminate()
                except Exception: pass
        return False
    def is_online(self):
        try: self._json("/api/tags",timeout=3); return True
        except Exception: return False
    def list_models(self):
        try: return [m.get("name","") for m in self._json("/api/tags",timeout=5).get("models",[])]
        except Exception: return []
    def cancel(self,model):
        with self._lock:
            connection=self._connection
            self._connection=None
        if connection:
            try: connection.close()
            except Exception: pass
        candidates=[Path.home()/"AppData/Local/Programs/Ollama/ollama.exe",Path("ollama.exe")]
        exe=next((str(p) for p in candidates if p.exists()),"ollama")
        try:
            p=subprocess.run([exe,"stop",model],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=8)
            return {"success":p.returncode==0,"model":model,"stderr":p.stderr}
        except Exception as exc: return {"success":False,"model":model,"error":str(exc)}
    def _messages(self,messages):
        converted=[]
        for source in messages:
            msg={"role":source.get("role","user"),"content":source.get("content") or ""}
            image_path=source.get("image_path")
            if image_path and Path(image_path).is_file():
                import base64
                msg["images"]=[base64.b64encode(Path(image_path).read_bytes()).decode("ascii")]
            if source.get("images"): msg["images"]=source["images"]
            if source.get("tool_calls"):
                calls=[]
                for raw in source["tool_calls"]:
                    fn=raw.get("function",raw); args=fn.get("arguments",{})
                    if isinstance(args,str):
                        try: args=json.loads(args)
                        except Exception: args={}
                    calls.append({"function":{"name":fn.get("name"),"arguments":args}})
                msg["tool_calls"]=calls
            if msg["role"]=="tool" and source.get("name"): msg["tool_name"]=source["name"]
            converted.append(msg)
        return converted
    def chat(self,messages,model,temperature=0.2,tools=None,stop_event=None,on_stream=None):
        if not self.is_online() and not self.ensure_server(): raise RuntimeError("Ollama 未启动，且自动启动失败；请确认本机 Ollama 已安装")
        payload={"model":model,"messages":self._messages(messages),"stream":True,"options":{"temperature":temperature}}
        if tools: payload["tools"]=tools
        parsed=urlparse(self.base_url); connection=http.client.HTTPConnection(parsed.hostname,parsed.port or 80,timeout=self.timeout)
        with self._lock: self._connection=connection
        content=[]; reasoning=[]; tool_calls=[]
        connection.request("POST",(parsed.path.rstrip("/")+"/api/chat") or "/api/chat",body=json.dumps(payload,ensure_ascii=False).encode("utf-8"),headers={"Content-Type":"application/json"})
        response=connection.getresponse()
        if response.status>=400: raise RuntimeError(f"Ollama HTTP {response.status}: {response.read().decode('utf-8',errors='replace')}")
        try:
            while True:
                if stop_event and stop_event.is_set(): response.close(); return {"content":"","reasoning":"","tool_calls":[],"stopped":True}
                line=response.readline()
                if not line: break
                chunk=json.loads(line.decode("utf-8")); msg=chunk.get("message",{})
                if msg.get("content"):
                    content.append(msg["content"])
                    if on_stream: on_stream("content",msg["content"])
                if msg.get("thinking") or msg.get("reasoning"):
                    thought=msg.get("thinking") or msg.get("reasoning")
                    reasoning.append(thought)
                    if on_stream: on_stream("reasoning",thought)
                if msg.get("tool_calls"): tool_calls.extend(msg["tool_calls"])
                if chunk.get("done"): break
        finally:
            response.close(); connection.close()
            with self._lock:
                if self._connection is connection: self._connection=None
        return {"content":"".join(content),"reasoning":"".join(reasoning),"tool_calls":tool_calls,"stopped":False}
