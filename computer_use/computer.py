from __future__ import annotations
import ctypes,time
from pathlib import Path

class ComputerController:
    def __init__(self,permissions=None):
        self.permissions=permissions; self.stopped=False; self.last_action=""
        try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try: ctypes.windll.user32.SetProcessDPIAware()
            except Exception: pass
        try:
            import pyautogui; pyautogui.FAILSAFE=True; pyautogui.PAUSE=0.08; self.p=pyautogui
        except Exception: self.p=None
    def _ready(self):
        if self.stopped: raise RuntimeError("Computer Use 已停止")
        if not self.p: raise RuntimeError("PyAutoGUI 不可用")
    def resume(self): self.stopped=False; return {"success":True,"enabled":True}
    def stop(self): self.stopped=True; return {"success":True,"enabled":False}
    def status(self): return {"success":True,"ready":self.p is not None and not self.stopped,"stopped":self.stopped,"size":list(self.p.size()) if self.p else [0,0],"last_action":self.last_action}
    def screen_size(self): self._ready(); s=self.p.size(); return {"success":True,"width":s.width,"height":s.height}
    def mouse_position(self): self._ready(); p=self.p.position(); return {"success":True,"x":p.x,"y":p.y}
    def screenshot(self,path,region=None):
        self._ready(); p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
        image=self.p.screenshot(region=tuple(region) if region else None); image.save(p); self.last_action=f"screenshot {p}"
        return {"success":True,"path":str(p),"width":image.width,"height":image.height}
    def move_mouse(self,x,y,duration=0.2): self._ready(); self.p.moveTo(x,y,duration=duration); self.last_action=f"move {x},{y}"; return {"success":True,"x":x,"y":y}
    def click(self,x=None,y=None,button="left",clicks=1): self._ready(); self.p.click(x=x,y=y,button=button,clicks=clicks); self.last_action=f"{button} click {x},{y}"; return {"success":True}
    def double_click(self,x=None,y=None): return self.click(x,y,"left",2)
    def right_click(self,x=None,y=None): return self.click(x,y,"right",1)
    def mouse_down(self,button="left"): self._ready(); self.p.mouseDown(button=button); return {"success":True}
    def mouse_up(self,button="left"): self._ready(); self.p.mouseUp(button=button); return {"success":True}
    def drag(self,x,y,duration=0.5,button="left"): self._ready(); self.p.dragTo(x,y,duration=duration,button=button); self.last_action=f"drag {x},{y}"; return {"success":True}
    def scroll(self,amount): self._ready(); self.p.scroll(amount); return {"success":True,"amount":amount}
    def type_text(self,text,interval=0.02): self._ready(); self.p.write(text,interval=interval); self.last_action=f"typed {len(text)} chars"; return {"success":True,"characters":len(text)}
    def press_key(self,key): self._ready(); self.p.press(key); return {"success":True,"key":key}
    def hotkey(self,keys): self._ready(); self.p.hotkey(*keys); return {"success":True,"keys":keys}
    def list_windows(self):
        import pygetwindow as gw
        return {"success":True,"windows":[{"title":w.title,"left":w.left,"top":w.top,"width":w.width,"height":w.height} for w in gw.getAllWindows() if w.title]}
    def active_window(self):
        import pygetwindow as gw
        w=gw.getActiveWindow(); return {"success":True,"title":w.title if w else ""}
    def activate_window(self,title,wait=0.3):
        import pygetwindow as gw
        matches=gw.getWindowsWithTitle(title)
        if not matches: return {"success":False,"error":"Window not found","title":title}
        w=matches[0]; w.restore() if w.isMinimized else None; w.activate(); time.sleep(wait); return {"success":True,"title":w.title}
    def window_action(self,title,action):
        import pygetwindow as gw
        matches=gw.getWindowsWithTitle(title)
        if not matches: return {"success":False,"error":"Window not found"}
        w=matches[0]; {"minimize":w.minimize,"maximize":w.maximize,"restore":w.restore}[action](); return {"success":True,"title":w.title,"action":action}
