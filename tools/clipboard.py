try: import pyperclip
except ImportError: pyperclip=None
def read_clipboard(): return pyperclip.paste() if pyperclip else "剪贴板依赖未安装"
def write_clipboard(text):
    if not pyperclip: return {"ok":False,"error":"pyperclip 未安装"}
    pyperclip.copy(text); return {"ok":True}
