from datetime import datetime

def get_time():
    now = datetime.now().astimezone()
    return {"ok": True, "text": now.strftime("现在是 %Y年%m月%d日 %H:%M:%S，时区：%Z"), "iso": now.isoformat()}
