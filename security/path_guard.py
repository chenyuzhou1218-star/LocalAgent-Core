from pathlib import Path
class PathGuard:
    def __init__(self,root): self.root=Path(root).resolve()
    def check(self,path): p=Path(path).resolve(); return p==self.root or self.root in p.parents
