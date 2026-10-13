from __future__ import annotations
import base64
from pathlib import Path
from .ollama import OllamaProvider
from .openai_compatible import OpenAICompatibleProvider

class ModelManager:
    def __init__(self,config):
        self.config=config; self.provider_name=config.get("provider","ollama"); self.ollama=OllamaProvider(config.get("ollama_base_url","http://127.0.0.1:11434"),config.get("model_timeout",120)); self.api_provider=OpenAICompatibleProvider(config.get("base_url",""),config.get("api_key",""),config.get("model_timeout",120)); self.local_models=[]; self.api_models=[]; self.models=[]; self.role_models={}; self.last_online=False
        # Do not block the window while Ollama/API discovery is waiting on a socket.
        # MainWindow refreshes this in a worker after the first frame is visible.
        selected=config.get("model","")
        if selected: self.models=[selected]
        self._assign_roles()
    def _detect_roles(self,models=None):
        pool=models if models is not None else self.models
        def has(model, words): return any(word in model.lower() for word in words)
        vision=next((m for m in pool if has(m,("llava","vision","qwen2-vl","minicpm-v","moondream"))),"")
        reasoning=next((m for m in pool if has(m,("deepseek-r1","deepseek","qwq","reasoning","think"))),"")
        main=next((m for m in pool if m not in {vision,reasoning} and has(m,("llama","chat","qwen","mistral","gemma","phi","command"))),"")
        if not main: main=next((m for m in pool if m not in {vision,reasoning}),pool[0] if pool else "")
        return {"main":main,"reasoning":reasoning,"vision":vision}
    def _assign_roles(self):
        if self.models:
            self.role_models=self._detect_roles()
            self.config.setdefault("main_agent_model",self.role_models["main"])
            self.config.setdefault("reasoning_model",self.role_models["reasoning"])
            if not self.config.get("vision_model"): self.config["vision_model"]=self.role_models["vision"]
        selected=self.config.get("model","")
        if selected and self.capabilities(selected)["vision"] and self.config.get("main_agent_model"):
            self.config["model"]=self.config["main_agent_model"]
    def refresh(self):
        self.local_models=self.ollama.list_models()
        self.api_provider.configure(self.config.get("base_url",""),self.config.get("api_key",""),self.config.get("model_timeout",120))
        self.api_models=self.api_provider.list_models() if self.config.get("base_url") else []
        self.models=list(dict.fromkeys(self.local_models+self.api_models))
        self.last_online=bool(self.local_models if self.provider_name=="ollama" else self.api_models)
        active_models=self.local_models if self.provider_name=="ollama" else self.api_models
        if active_models:
            self.role_models=self._detect_roles(active_models)
            selected=self.config.get("model","")
            if selected not in active_models:
                self.config["model"]=self.role_models["main"]
            if self.config.get("main_agent_model") not in active_models:
                self.config["main_agent_model"]=self.role_models["main"]
            if self.config.get("reasoning_model") not in active_models:
                self.config["reasoning_model"]=self.role_models["reasoning"]
            if self.config.get("vision_model") not in active_models:
                self.config["vision_model"]=self.role_models["vision"]
        return self.models
    def api_provider_name(self):
        return "deepseek" if "deepseek.com" in self.config.get("base_url","").lower() else "openai-compatible"
    def model_options(self):
        options=[{"label":f"本地 · {model}","source":"ollama","model":model} for model in self.local_models]
        options += [{"label":f"API · {model}","source":"api","model":model} for model in self.api_models]
        active=self.active_model()
        if active and not any(item["model"]==active and ((self.provider_name=="ollama" and item["source"]=="ollama") or (self.provider_name!="ollama" and item["source"]=="api")) for item in options):
            options.append({"label":f"{'本地' if self.provider_name=='ollama' else 'API'} · {active}","source":"ollama" if self.provider_name=="ollama" else "api","model":active})
        return options
    def check_api_connection(self,provider=None,base_url=None,api_key=None):
        """Check a pending API configuration without changing the active provider."""
        name=provider or self.provider_name
        if name == "ollama":
            online=self.ollama.is_online()
            return {"success":online,"message":"Ollama 已连接" if online else "Ollama 未连接"}
        self.api_provider.configure(base_url if base_url is not None else self.config.get("base_url",""),api_key if api_key is not None else self.config.get("api_key",""),self.config.get("model_timeout",120))
        return self.api_provider.check_connection()
    def online(self):
        return self.last_online
    def set_model(self,model): self.config["model"]=model
    def set_model_choice(self,model,source):
        self.provider_name="ollama" if source=="ollama" else self.api_provider_name()
        self.config["provider"]=self.provider_name
        self.config["model"]=model
    def set_vision_model(self,model): self.config["vision_model"]=model
    def active_model(self): return self.config.get("model") or (self.models[0] if self.models else "")
    def capabilities(self,model=None):
        name=(model or self.active_model()).lower(); vision=any(x in name for x in ("llava","vision","qwen2-vl","minicpm-v")); reasoning=any(x in name for x in ("deepseek-r1","reasoning","qwq")); tools=not vision and not reasoning and bool(name)
        return {"text":True,"tools":tools,"vision":vision,"reasoning":reasoning}
    def reasoning_options(self,model=None):
        """Return only effort levels known to be accepted by the selected API model."""
        name=(model or self.active_model()).lower()
        if self.provider_name == "ollama":
            return []
        if "deepseek-flash" in name or "deepseek-v4" in name:
            return [("关闭思考", "none"), ("低", "low"), ("高", "high"), ("专家/极高", "max")]
        if "deepseek" in name:
            return []
        if "gpt-5.1-codex-max" in name or "codex-max" in name:
            return [("低", "low"), ("中", "medium"), ("高", "high"), ("极高", "xhigh")]
        if "codex" in name:
            return [("低", "low"), ("中", "medium"), ("高", "high")]
        if "gpt-5.1" in name:
            return [("关闭", "none"), ("低", "low"), ("中", "medium"), ("高", "high")]
        if any(token in name for token in ("gpt-5", " o1", "o1-", "o3", "o4")):
            return [("低", "low"), ("中", "medium"), ("高", "high")]
        return []
    def chat(self,messages,tools=None,stop_event=None,on_stream=None):
        model=self.active_model()
        if tools and not self.capabilities(model)["tools"]: model=self.config.get("main_agent_model") or model
        if not model: raise RuntimeError("没有可用文本模型，请启动 Ollama 并在模型页面选择模型")
        if self.provider_name=="ollama": return self.ollama.chat(messages,model,self.config.get("temperature",0.2),tools,stop_event,on_stream)
        self.api_provider.configure(self.config.get("base_url",""),self.config.get("api_key",""),self.config.get("model_timeout",120)); return self.api_provider.chat(messages,model,self.config.get("temperature",0.2),tools,stop_event,on_stream,self.config.get("reasoning_effort") if self.config.get("reasoning_effort") in {value for _,value in self.reasoning_options(model)} else None)
    def cancel_active(self):
        if self.provider_name=="ollama" and self.active_model(): return self.ollama.cancel(self.active_model())
        return self.api_provider.cancel()
    def vision_chat(self,path,prompt="请结构化描述当前屏幕，列出可交互元素及大致坐标"):
        model=self.config.get("vision_model") or next((m for m in self.models if self.capabilities(m)["vision"]),"")
        if not model: return "没有配置视觉模型。"
        suffix=Path(path).suffix.lower()
        if suffix not in {".png",".jpg",".jpeg",".webp",".bmp"}: return "视觉模型当前接受图片或已提取的视频帧，不直接处理完整视频文件。"
        image=base64.b64encode(Path(path).read_bytes()).decode("ascii")
        result=self.ollama.chat([{"role":"user","content":prompt,"images":[image]}],model,self.config.get("temperature",0.2))
        return result.get("content") or result.get("reasoning") or "视觉模型没有返回内容。"
