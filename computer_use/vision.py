class Vision:
    def encode(self,path):
        import base64
        return base64.b64encode(open(path,"rb").read()).decode()
