from pathlib import Path
import shutil
class FolderTools:
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
        if str(p).lower().startswith("c:\\windows"): raise PermissionError("核心系统路径受保护")
        return p
    def create_folder(self,path):
        p=self._p(path)
        if p.suffix.lower() in {".txt",".py",".json",".md",".html",".css",".js",".yaml",".yml",".csv",".ini",".toml"}: return {"success":False,"error":"Path looks like a file; use write_file instead","path":str(p)}
        p.mkdir(parents=True,exist_ok=True); exists=p.is_dir(); return {"success":exists,"path":str(p),"verified":exists}
    def list_folder(self,path="."):
        p=self._p(path); items=[{"name":x.name,"path":str(x),"type":"folder" if x.is_dir() else "file","size":x.stat().st_size if x.is_file() else None} for x in p.iterdir()]; return {"success":True,"path":str(p),"items":items}
    def copy_folder(self,source,destination): src,dst=self._p(source),self._p(destination); shutil.copytree(src,dst,dirs_exist_ok=True); return {"success":True,"source":str(src),"destination":str(dst)}
    def move_folder(self,source,destination): src,dst=self._p(source),self._p(destination); shutil.move(str(src),str(dst)); return {"success":True,"source":str(src),"destination":str(dst)}
    def rename_folder(self,path,new_name): p=self._p(path); dst=p.with_name(new_name); p.rename(dst); return {"success":True,"path":str(dst)}
    def delete_folder(self,path): p=self._p(path); shutil.rmtree(p); return {"success":True,"path":str(p)}
