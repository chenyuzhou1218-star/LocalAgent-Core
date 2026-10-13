class Keyboard:
    def __init__(self): import pyautogui; self.p=pyautogui
    def write(self,text): self.p.write(text)
    def press(self,key): self.p.press(key)
    def hotkey(self,*keys): self.p.hotkey(*keys)
