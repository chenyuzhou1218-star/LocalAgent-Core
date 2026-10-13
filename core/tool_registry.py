from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass
class ToolDefinition:
    name: str
    executor: Callable[..., Any]
    description: str
    parameters: dict[str, Any] = field(default_factory=lambda: {"type":"object","properties":{}})
    group: str = "SYSTEM"
    risk: str = "low"

class ToolRegistry:
    def __init__(self): self._tools: dict[str,ToolDefinition] = {}
    def register(self,name,fn,description="",parameters=None,group="SYSTEM",risk="low"):
        if not callable(fn): raise TypeError(f"Tool {name} executor is not callable")
        if name in self._tools: raise ValueError(f"Duplicate tool: {name}")
        self._tools[name]=ToolDefinition(name,fn,description,parameters or {"type":"object","properties":{}},group,risk)
    def names(self): return list(self._tools)
    def definition(self,name): return self._tools.get(name)
    def schemas(self,groups=None):
        selected=self._tools.values() if not groups else (t for t in self._tools.values() if t.group in groups)
        return [{"type":"function","function":{"name":t.name,"description":t.description,"parameters":t.parameters}} for t in selected]
    def descriptions(self): return {k:v.description for k,v in self._tools.items()}
    def self_check(self): return {name:{"ok":callable(t.executor),"group":t.group,"risk":t.risk} for name,t in self._tools.items()}
    def execute(self,name,arguments=None):
        tool=self._tools.get(name)
        if not tool: return {"success":False,"error":f'Tool "{name}" does not exist',"available":self.names()}
        args=arguments or {}
        if not isinstance(args,dict): return {"success":False,"error":"Tool arguments must be a JSON object"}
        required=tool.parameters.get("required",[])
        missing=[key for key in required if key not in args]
        if missing: return {"success":False,"error":"Missing required arguments: "+", ".join(missing)}
        allowed=set(tool.parameters.get("properties",{}))
        if allowed: args={k:v for k,v in args.items() if k in allowed}
        try:
            result=tool.executor(**args)
            if isinstance(result,dict):
                result.setdefault("success",result.pop("ok",True)); return result
            return {"success":True,"result":result}
        except Exception as exc: return {"success":False,"error":f"{type(exc).__name__}: {exc}"}
    def groups_for_task(self,text):
        low=text.lower(); groups={"SYSTEM"}
        if any(x in low for x in ("计算","算一下","等于多少","换算","单位","calculator","convert")): groups|={"SYSTEM"}
        if any(x in low for x in ("文件","文件夹","目录","代码","项目","file","folder")): groups|={"FILES","TERMINAL","PROGRAM"}
        if any(x in low for x in ("命令","运行","终端","powershell","cmd","python","安装","execute","terminal")): groups|={"TERMINAL","PROGRAM","FILES"}
        if any(x in low for x in ("电脑","此电脑","我的电脑","文件管理器","鼠标","键盘","窗口","截图","记事本","computer","this pc","my pc","file explorer","click","type")): groups|={"COMPUTER","PROGRAM"}
        if any(x in low for x in ("打开电脑","打开pc","open pc","open computer","open this pc","open file explorer")): groups|={"PROGRAM","COMPUTER"}
        if any(x in low for x in ("网页","网站","浏览器","登录","browser","http")): groups|={"BROWSER"}
        if any(x in low for x in ("剪贴板","clipboard")): groups|={"CLIPBOARD"}
        if any(x in low for x in ("项目","代码库","代码项目","project","repo","仓库","结构","理解代码")): groups|={"PROJECT"}
        if any(x in low for x in ("审查","review","bug","错误","语法","检查代码")): groups|={"REVIEW","PROJECT"}
        if any(x in low for x in ("测试","编译","pytest","test")): groups|={"REVIEW","TERMINAL","PROJECT"}
        if any(x in low for x in ("插件","mcp","skill","扩展")): groups|={"EXTENSIONS"}
        return groups
