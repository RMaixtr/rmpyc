from upydevice import WebSocketDevice

class rmpyc(WebSocketDevice):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.open_wconn()
        self.kbi()
        self.banner(pipe=self.sres)
        self.modules = RemoteModule(self)

    def sres(self, output, asciigraphicscode=None, std="stdout", execute_prompt=False):
        print("sres", output)


class RemoteModule:
    def __init__(self, client: WebSocketDevice):
        self.client = client

    def __dir__(self):
        print("dir(" + self.attribute_path + ")")

    def __getitem__(self, key: str):
        self.client.wr_cmd("import " + key)
        return getattr(self, key)

    def __getattr__(self, name: str):
        return RemoteAttribute(self.client, name)

class RemoteAttribute:
    def __init__(self, client: WebSocketDevice, attribute_path: str):
        self.client = client
        self.attribute_path = attribute_path

    def __str__(self) -> str:
        return self.client.wr_cmd(self.attribute_path, silent = True, rtn_resp=True)
    
    def __dir__(self):
        return self.client.wr_cmd("dir(" + self.attribute_path + ")", silent = True, rtn_resp=True)

    def __call__(self, *args, **kwargs):
        args_str = ', '.join(map(repr, args))
        kwargs_str = ', '.join(f"{k}={repr(v)}" for k, v in kwargs.items())
        params_str = ', '.join(filter(None, [args_str, kwargs_str]))
        command = f"{self.attribute_path}({params_str})"
        # print(command)
        return self.client.wr_cmd(command, silent = True, rtn_resp=True)

    def __getattr__(self, name):
        return RemoteAttribute(self.client, f"{self.attribute_path}.{name}")