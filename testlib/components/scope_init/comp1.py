from .comp0 import Comp0
from . import sharedbuf

outer = "comp1Outer"


class Comp1(Comp0):
    template = "<<outer>>, <<self.arg1>>"

    def __init__(self, arg1):
        sharedbuf.write({"component": "comp1", "msg": "pre", "args": [arg1]})
        super().__init__(arg1, "comp1:arg2")
        sharedbuf.write({"component": "comp1", "msg": "post"})
