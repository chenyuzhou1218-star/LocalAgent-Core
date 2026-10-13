class VisionModel:
    def __init__(self,provider,model=""): self.provider=provider; self.model=model
    def describe(self,image_base64,prompt="描述这张屏幕截图"): return "视觉模型未配置" if not self.model else self.provider.chat([{"role":"user","content":prompt,"images":[image_base64]}],self.model)
