class RiskChecker:
    def risk(self,action,target=""): return "critical" if any(x in action.lower() for x in ("delete","format","uac")) else "low"
