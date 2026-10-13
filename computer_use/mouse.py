class Mouse:
    def __init__(self): import pyautogui; pyautogui.FAILSAFE=True; self.p=pyautogui
    def move(self,x,y): self.p.moveTo(x,y)
    def click(self,x=None,y=None,button="left",clicks=1): self.p.click(x,y,clicks=clicks,button=button)
    def drag(self,x,y,duration=.3): self.p.dragTo(x,y,duration=duration)
    def scroll(self,amount): self.p.scroll(amount)
