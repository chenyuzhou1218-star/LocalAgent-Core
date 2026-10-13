import json, logging, re
SECRET=re.compile(r"(?i)(api[_-]?key|token|password|secret)(\s*[=:]\s*)[^,\s]+")
def setup_logger(root):
    root.mkdir(parents=True,exist_ok=True); logger=logging.getLogger("local_agent"); logger.setLevel(logging.INFO)
    if not logger.handlers:
        h=logging.FileHandler(root/"agent.log",encoding="utf-8"); h.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")); logger.addHandler(h)
    return logger
def redact(value):
    text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,default=str)
    return SECRET.sub(r"\1\2[REDACTED]",text)
