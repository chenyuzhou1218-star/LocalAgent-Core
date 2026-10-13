from collections import defaultdict
class EventBus:
    def __init__(self): self.listeners=defaultdict(list)
    def subscribe(self,event,callback): self.listeners[event].append(callback)
    def emit(self,event,*args,**kwargs):
        for cb in list(self.listeners.get(event,[])):
            try: cb(*args,**kwargs)
            except Exception: pass
