import base64, http.client, json, mimetypes, threading, urllib.error, urllib.request
from pathlib import Path
from urllib.parse import urlparse
class OpenAICompatibleProvider:
    def __init__(self,base_url,api_key="",timeout=None): self.base_url=base_url.rstrip("/"); self.api_key=api_key; self.timeout=timeout; self._connection=None; self._lock=threading.Lock()
    def configure(self,base_url=None,api_key=None,timeout=None):
        if base_url is not None: self.base_url=base_url.rstrip("/")
        if api_key is not None: self.api_key=api_key
        if timeout is not None: self.timeout=timeout
    def _headers(self):
        headers={"Content-Type":"application/json"}
        if self.api_key: headers["Authorization"]="Bearer "+self.api_key
        return headers
    def _messages_with_images(self,messages):
        converted=[]
        for source in messages:
            item=dict(source)
            image_path=item.pop("image_path",None)
            if image_path:
                path=Path(image_path)
                if path.is_file():
                    mime=mimetypes.guess_type(str(path))[0] or "image/png"
                    encoded=base64.b64encode(path.read_bytes()).decode("ascii")
                    text=item.get("content") or "请分析这张图片。"
                    item["content"]=[
                        {"type":"text","text":text},
                        {"type":"image_url","image_url":{"url":f"data:{mime};base64,{encoded}"}},
                    ]
            converted.append(item)
        return converted
    def _request_json(self,path,payload=None,timeout=None):
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None
        req=urllib.request.Request(self.base_url+path,data=data,headers=self._headers())
        try:
            with urllib.request.urlopen(req,timeout=timeout or self.timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail=exc.read().decode("utf-8",errors="replace")
            raise RuntimeError(f"API HTTP {exc.code}: {detail[:1000]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"API 连接失败：{exc.reason}") from exc
    def list_models(self):
        if not self.base_url: return []
        try:
            data=self._request_json("/models",timeout=8)
            return [item.get("id","") for item in data.get("data",[]) if item.get("id")]
        except Exception:
            return []
    def is_online(self): return bool(self.list_models())
    def check_connection(self):
        if not self.base_url: return {"success":False,"error":"没有填写 API 地址"}
        try:
            models=self.list_models()
            if not models:
                return {"success":False,"error":"接口可访问，但没有返回可用模型；请检查 API Key、地址和账号权限"}
            return {"success":True,"models":models,"message":f"连接成功，发现 {len(models)} 个模型"}
        except Exception as exc:
            return {"success":False,"error":str(exc)}
    def chat(self,messages,model,temperature=0.2,tools=None,stop_event=None,on_stream=None,reasoning_effort=None):
        if stop_event and stop_event.is_set():
            return {"content":"","reasoning":"","tool_calls":[],"stopped":True}
        body={"model":model,"messages":self._messages_with_images(messages),"temperature":temperature,"stream":bool(on_stream and not tools)}
        if reasoning_effort:
            body["reasoning_effort"]=reasoning_effort
            if "deepseek" in model.lower():
                body["thinking"]={"type":"disabled" if reasoning_effort == "none" else "enabled"}
        if tools: body.update({"tools":tools,"tool_choice":"auto"})
        parsed=urlparse(self.base_url); connection_class=http.client.HTTPSConnection if parsed.scheme=="https" else http.client.HTTPConnection
        connection=connection_class(parsed.hostname,parsed.port or (443 if parsed.scheme=="https" else 80),timeout=self.timeout)
        target=(parsed.path.rstrip("/") or "")+"/chat/completions"
        with self._lock: self._connection=connection
        response=None
        try:
            connection.request("POST",target,body=json.dumps(body,ensure_ascii=False).encode("utf-8"),headers=self._headers())
            if stop_event and stop_event.is_set():
                connection.close()
                return {"content":"","reasoning":"","tool_calls":[],"stopped":True}
            response=connection.getresponse()
            if response.status>=400:
                detail=response.read().decode("utf-8",errors="replace")
                raise RuntimeError(f"API HTTP {response.status}: {detail[:1000]}")
            if on_stream and not tools:
                content=[]; reasoning=[]; tool_calls=[]
                while True:
                    if stop_event and stop_event.is_set(): return {"content":"","reasoning":"","tool_calls":[],"stopped":True}
                    raw=response.readline()
                    if not raw: break
                    line=raw.decode("utf-8",errors="replace").strip()
                    if not line or line=="data: [DONE]": continue
                    if line.startswith("data:"): line=line[5:].strip()
                    try: chunk=json.loads(line)
                    except json.JSONDecodeError: continue
                    delta=chunk.get("choices",[{}])[0].get("delta",{})
                    piece=delta.get("content") or ""
                    thought=delta.get("reasoning_content") or delta.get("reasoning") or ""
                    if piece: content.append(piece); on_stream("content",piece)
                    if thought: reasoning.append(thought); on_stream("reasoning",thought)
                    if delta.get("tool_calls"): tool_calls.extend(delta["tool_calls"])
                return {"content":"".join(content),"reasoning":"".join(reasoning),"tool_calls":tool_calls,"stopped":False}
            if stop_event and stop_event.is_set():
                return {"content":"","reasoning":"","tool_calls":[],"stopped":True}
            data=json.loads(response.read().decode("utf-8"))
            msg=data["choices"][0]["message"]
            return {"content":msg.get("content") or "","reasoning":msg.get("reasoning_content") or msg.get("reasoning") or "","tool_calls":msg.get("tool_calls") or [],"stopped":False}
        except (OSError,http.client.HTTPException) as exc:
            if stop_event and stop_event.is_set(): return {"content":"","reasoning":"","tool_calls":[],"stopped":True}
            raise RuntimeError(f"API 连接失败：{exc}") from exc
        finally:
            try: response.close()
            except Exception: pass
            connection.close()
            with self._lock:
                if self._connection is connection: self._connection=None
    def cancel(self):
        with self._lock:
            connection=self._connection
            self._connection=None
        if connection:
            try: connection.close()
            except Exception: pass
        return {"success":True,"cancelled":bool(connection)}
