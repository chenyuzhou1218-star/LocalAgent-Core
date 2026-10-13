from pathlib import Path
class Screen:
    def size(self):
        try:
            import pyautogui; return pyautogui.size()
        except Exception: return (0,0)
    def screenshot(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        try:
            import mss
            with mss.mss() as s: s.shot(output=str(path))
            return str(path)
        except Exception as exc: return f"截图不可用：{exc}"
