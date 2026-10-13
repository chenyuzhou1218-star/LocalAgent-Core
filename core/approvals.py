from dataclasses import dataclass
from enum import Enum
class PermissionMode(str,Enum): ASK_ALL="ask_all"; ASK_RISKY="ask_risky"; UNRESTRICTED="unrestricted"
@dataclass
class ApprovalRequest: action:str; target:str; reason:str; risk:str="medium"
