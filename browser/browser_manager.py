from __future__ import annotations
from pathlib import Path
class BrowserManager:
    def __init__(self,profile_dir=None): self.profile_dir=str(profile_dir) if profile_dir else None; self._pw=None; self.context=None; self.page=None
    def available(self):
        try: import playwright.sync_api; return True
        except Exception: return False
    def open(self,url="about:blank",headless=False):
        if not self.available(): return {"success":False,"error":"Playwright 未安装"}
        from playwright.sync_api import sync_playwright
        if not self._pw:
            self._pw=sync_playwright().start()
            if self.profile_dir: self.context=self._pw.chromium.launch_persistent_context(self.profile_dir,headless=headless)
            else: self.context=self._pw.chromium.launch(headless=headless).new_context()
            self.page=self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.goto(url,wait_until="domcontentloaded",timeout=30000); return {"success":True,"url":self.page.url,"title":self.page.title()}
    def navigate(self,url): return self.open(url) if not self.page else self._nav(url)
    def _nav(self,url): self.page.goto(url,wait_until="domcontentloaded",timeout=30000); return {"success":True,"url":self.page.url,"title":self.page.title()}
    def new_tab(self,url="about:blank"): self.page=self.context.new_page(); return self._nav(url)
    def tabs(self): return {"success":True,"tabs":[{"index":i,"url":p.url,"title":p.title()} for i,p in enumerate(self.context.pages)]}
    def switch_tab(self,index): self.page=self.context.pages[index]; self.page.bring_to_front(); return {"success":True,"index":index,"url":self.page.url}
    def click(self,selector): self.page.locator(selector).click(timeout=15000); return {"success":True,"selector":selector}
    def type(self,selector,text,press_enter=False): self.page.locator(selector).fill(text); self.page.locator(selector).press("Enter") if press_enter else None; return {"success":True,"selector":selector}
    def read_page(self,max_chars=20000): return {"success":True,"url":self.page.url,"title":self.page.title(),"text":self.page.locator("body").inner_text()[:max_chars]}
    def scroll(self,amount=700): self.page.mouse.wheel(0,amount); return {"success":True,"amount":amount}
    def screenshot(self,path): p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); self.page.screenshot(path=str(p),full_page=False); return {"success":True,"path":str(p)}
    def back(self): self.page.go_back(); return {"success":True,"url":self.page.url}
    def forward(self): self.page.go_forward(); return {"success":True,"url":self.page.url}
    def refresh(self): self.page.reload(); return {"success":True,"url":self.page.url}
    def close(self):
        if self.context: self.context.close()
        if self._pw: self._pw.stop()
        self.context=self.page=self._pw=None; return {"success":True}
