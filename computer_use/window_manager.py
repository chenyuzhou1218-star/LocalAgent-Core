class WindowManager:
    def __init__(self):
        try: import pygetwindow as gw; self.gw=gw
        except ImportError: self.gw=None
    def current(self): return self.gw.getActiveWindowTitle() if self.gw else "窗口依赖未安装"
    def list(self): return [w.title for w in self.gw.getAllWindows()] if self.gw else []
