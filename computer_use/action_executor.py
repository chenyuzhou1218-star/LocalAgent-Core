class ActionExecutor:
    def __init__(self,permissions): self.permissions=permissions
    def run(self,action,target,fn,*args,**kwargs):
        if not self.permissions.decide(action,target,"Computer Use 操作","high"): return {"ok":False,"error":"已拒绝"}
        try: return {"ok":True,"result":fn(*args,**kwargs)}
        except Exception as exc: return {"ok":False,"error":str(exc)}
