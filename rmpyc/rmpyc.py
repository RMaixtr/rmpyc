
from upydevice.natsdevice import NatsDevice, CustomFunction
from dill.source import getsource
import functools

class rmpyc(NatsDevice):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.remote = RemoteModule(self)
        self.callfun = {}

    def callback(self, msg:bytes):
        self.callfun[msg.decode()]()


    def remotecall(self, locfun):
        self.callfun[locfun.__name__] = locfun
        def fun(remotefun):
            source_lines = getsource(remotefun).split('\n')[1:]
            indent = len(source_lines[0]) - len(source_lines[0].lstrip())
            tab = len(source_lines[1]) - len(source_lines[1].lstrip())
            source_lines.insert(1, tab * ' ' + 'Webrepl.nc.publish(b"mpy.repl.callback", "'+ locfun.__name__ +'")')
            str_func = '\n'.join([line[indent:] for line in source_lines if line.strip()])

            self.paste_buff(str_func)
            self.cmd('\x04', silent=True)

            @functools.wraps(remotefun)
            def wrapper_cmd(*args, **kwargs):
                flags = ['>', '<', 'object', 'at', '0x']
                args_repr = [repr(a) for a in args if any(
                    f not in repr(a) for f in flags)]
                kwargs_repr = [f"{k}={v!r}" if not callable(
                    v) else f"{k}={v.__name__}" for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
                cmd_ = f"{remotefun.__name__}({signature})"
                self.wr_cmd(cmd_, rtn=True)
                if self.output:
                    return self.output

            return CustomFunction(wrapper_cmd)
        return fun


class RemoteModule:
    def __init__(self, client: NatsDevice):
        self.__client__ = client

    def __getattr__(self, name: str):
        return RemoteAttribute(self.__client__, name)

    def __setattr__(self, name, value):
        if name.startswith('__') and name.endswith('__') and len(name) > 4:
            super().__setattr__(name, value)
        else:
            self.__client__.wr_cmd(f"{name}=globals()['__remotetmp__']", silent = True, rtn_resp=True)
    

class RemoteAttribute():
    def __init__(self, client: NatsDevice, attribute_path: str):
        self.__client__ = client
        self.__attribute_path__ = attribute_path

    def __repr__(self) -> str:
        return str(self.__attribute_path__)

    def __str__(self) -> str:
        return str(self.__client__.wr_cmd(self.__attribute_path__, silent = True, rtn_resp=True))
    
    def __dir__(self):
        return self.__client__.wr_cmd("dir(" + self.__attribute_path__ + ")", silent = True, rtn_resp=True)

    def __call__(self, *args, **kwargs):
        flags = ['>', '<', 'object', 'at', '0x']
        args_repr = [repr(a) for a in args if any(
            f not in repr(a) for f in flags)]
        kwargs_repr = [f"{k}={v!r}" if not callable(
            v) else f"{k}={v.__name__}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        cmd_ = f"__remotetmp__ = {self.__attribute_path__}({signature})"
        self.__client__.wr_cmd(cmd_)
        self.__client__.wr_cmd("__remotetmp__", rtn=True)
        if self.__client__.output:
            return self.__client__.output

    def __getattr__(self, name):
        return RemoteAttribute(self.__client__, f"{self.__attribute_path__}.{name}")
    
    def __setattr__(self, name, value):
        if name.startswith('__') and name.endswith('__') and len(name) > 4:
            super().__setattr__(name, value)
        else:
            self.__client__.wr_cmd(f"{self.__attribute_path__}.{name}=globals()['__remotetmp__']", silent = True, rtn_resp=True)

    