from __future__ import annotations
from pathlib import Path
import shutil
class FileTools:
    def __init__(self,root): self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True)
    def _p(self,path):
        raw=str(path or '').strip().replace('/', '\\'); low=raw.lower()
        if low in {'桌面','desktop'}: p=Path.home()/'Desktop'
        elif low.startswith('桌面\\') or low.startswith('desktop\\'): p=Path.home()/'Desktop'/raw.split('\\',1)[1]
        elif low.startswith('c:\\users\\username\\desktop'):
            suffix=raw[len('C:\\Users\\username\\Desktop'):].lstrip('\\'); p=Path.home()/'Desktop'/suffix
        else:
            p=Path(raw); p=(self.root/p) if not p.is_absolute() else p
        p=p.resolve()
        low=str(p).lower()
        if low.startswith("c:\\windows") or low.startswith("c:\\program files\\windows defender"): raise PermissionError("核心系统路径受保护")
        return p
    def read_file(self,path,max_chars=200000): p=self._p(path); return {"success":True,"path":str(p),"content":p.read_text(encoding="utf-8",errors="replace")[:max_chars],"size":p.stat().st_size}
    def write_file(self,path,content,overwrite=True):
        p=self._p(path)
        if p.exists() and not overwrite: return {"success":False,"error":"File already exists","path":str(p)}
        p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding="utf-8"); exists=p.is_file(); return {"success":exists,"path":str(p),"size":p.stat().st_size if exists else 0,"verified":exists}
    def append_file(self,path,content): p=self._p(path); p.parent.mkdir(parents=True,exist_ok=True); p.open("a",encoding="utf-8").write(content); exists=p.is_file(); return {"success":exists,"path":str(p),"size":p.stat().st_size if exists else 0,"verified":exists}
    def copy_file(self,source,destination): src,dst=self._p(source),self._p(destination); dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst); return {"success":True,"source":str(src),"destination":str(dst)}
    def move_file(self,source,destination): src,dst=self._p(source),self._p(destination); dst.parent.mkdir(parents=True,exist_ok=True); shutil.move(str(src),str(dst)); return {"success":True,"source":str(src),"destination":str(dst)}
    def rename_file(self,path,new_name): p=self._p(path); dst=p.with_name(new_name); p.rename(dst); return {"success":True,"path":str(dst)}
    def delete_file(self,path): p=self._p(path); p.unlink(); return {"success":True,"path":str(p)}
    def file_info(self,path): p=self._p(path); s=p.stat(); return {"success":True,"path":str(p),"size":s.st_size,"modified":s.st_mtime,"is_file":p.is_file()}
    def search_files(self,query,path=".",limit=100):
        base=self._p(path); items=[]
        for p in base.rglob(f"*{query}*"):
            items.append(str(p))
            if len(items)>=limit: break
        return {"success":True,"items":items,"count":len(items)}
