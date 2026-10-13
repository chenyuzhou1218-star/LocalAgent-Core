class CommandGuard:
    blocked=("format ","shutdown","del c:\\windows","remove-item c:\\windows")
    def check(self,command): return not any(x in command.lower() for x in self.blocked)
