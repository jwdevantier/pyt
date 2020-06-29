from .comp1 import Comp1
from . import sharedbuf

outer = "comp2Outer"


class Comp2(Comp1):
    template = "<<outer>> <<self.arg1>>, <<self.arg2>>, <<self.arg3>>"

    def __init__(self, arg1):
        sharedbuf.write({"component": "comp2", "msg": "pre", "args": [arg1]})
        super().__init__("comp2:fixed_arg")
        sharedbuf.write({"component": "comp2", "msg": "post"})
