from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.agent_loop import AgentLoop
from core.approvals import PermissionMode
from core.permissions import PermissionManager
from core.event_bus import EventBus
from core.task_manager import Task,TaskStatus
from core.tool_registry import ToolRegistry
from core.logger import setup_logger
from tools.files import FileTools
from tools.folders import FolderTools

TEST=ROOT/"workspace"/"test_agent_tools"

class FakeModel:
    def __init__(self): self.calls=0; self.tool_calls=0; self.received_tools=[]
    def chat(self,messages,tools=None,stop_event=None):
        self.calls+=1; self.received_tools=tools or []
        if not tools: return {"content":"我会先执行当前步骤，然后根据工具结果继续。","tool_calls":[],"stopped":False}
        self.tool_calls+=1
        if self.tool_calls==1: return {"content":"","tool_calls":[{"id":"call_1","function":{"name":"create_folder","arguments":{"path":"test_agent_tools"}}}],"stopped":False}
        if self.tool_calls==2: return {"content":"","tool_calls":[{"id":"call_2","function":{"name":"write_file","arguments":{"path":"test_agent_tools/hello.txt","content":"Hello Agent"}}}],"stopped":False}
        return {"content":"任务已真实完成。","tool_calls":[],"stopped":False}

def run():
    if TEST.exists(): shutil.rmtree(TEST)
    registry=ToolRegistry(); files=FileTools(ROOT/"workspace"); folders=FolderTools(ROOT/"workspace")
    path_schema={"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}
    registry.register("create_folder",folders.create_folder,"create",path_schema,"FILES")
    registry.register("write_file",files.write_file,"write",{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]},"FILES")
    model=FakeModel(); loop=AgentLoop(model,registry,PermissionManager(PermissionMode.UNRESTRICTED),setup_logger(ROOT/"logs"),EventBus(),10); task=Task("创建文件夹并写入 hello.txt")
    reply=loop.run(task,[])
    assert task.status==TaskStatus.COMPLETED
    assert (TEST/"hello.txt").read_text(encoding="utf-8")=="Hello Agent"
    assert model.calls==6 and model.tool_calls==3 and len(model.received_tools)==2
    shutil.rmtree(TEST)
    print("AGENT_LOOP_OK",reply)

if __name__=="__main__": run()
