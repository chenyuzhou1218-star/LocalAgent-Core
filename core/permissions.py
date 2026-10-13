from .approvals import PermissionMode,ApprovalRequest
class PermissionManager:
    HARD_BLOCK=("disable_defender","bypass_uac","steal_password","steal_cookie","format_disk","keylogger")
    def __init__(self,mode=PermissionMode.ASK_RISKY,callback=None): self.mode=PermissionMode(mode); self.callback=callback
    def set_mode(self,mode): self.mode=PermissionMode(mode)
    def decide(self,action,target="",reason="",risk="medium",force=False):
        hay=(action+" "+target).lower()
        if any(x in hay for x in self.HARD_BLOCK) or "c:\\windows\\system32" in hay: return False
        needs=force or self.mode==PermissionMode.ASK_ALL or (self.mode==PermissionMode.ASK_RISKY and risk in {"high","critical"})
        if not needs: return True
        return bool(self.callback(ApprovalRequest(action,target,reason,risk))) if self.callback else False
