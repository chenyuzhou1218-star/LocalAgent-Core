from dataclasses import dataclass,field
from datetime import datetime
from enum import Enum
from threading import Event
from uuid import uuid4
class TaskStatus(str,Enum): WAITING="等待"; THINKING="思考"; RUNNING_TOOL="运行工具"; WAITING_PERMISSION="等待权限"; RUNNING="运行中"; COMPLETED="已完成"; FAILED="失败"; STOPPED="已停止"
@dataclass
class Task:
    text:str; image_path:str=""; status:TaskStatus=TaskStatus.WAITING; step:str=""; id:str=field(default_factory=lambda:uuid4().hex[:12]); started_at:str=field(default_factory=lambda:datetime.now().astimezone().isoformat()); completed_steps:list=field(default_factory=list); error:str=""; result:str=""
    def __post_init__(self): self.stop_event=Event()
    def stop(self): self.stop_event.set(); self.status=TaskStatus.STOPPED; self.step="已停止"
    @property
    def stopped(self): return self.stop_event.is_set()
