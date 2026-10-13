from .path_guard import PathGuard
from .command_guard import CommandGuard
class Sandbox:
    def __init__(self,root): self.paths=PathGuard(root); self.commands=CommandGuard()
