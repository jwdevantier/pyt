from ghostwriter.utils.cogen.component import Component
from . import sharedbuf

outer = "comp0Outer"


class Comp0(Component):
    template = "<<outer>>, <<self.arg1>>, <<self.arg2>>"

    def __init__(self, arg1, arg2):
        sharedbuf.write({"component": "comp0", "msg": "pre", "args": [arg1, arg2]})
        self.arg1 = arg1
        self.arg2 = arg2
        sharedbuf.write({"component": "comp0", "msg": "post"})
