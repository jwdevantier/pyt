from ghostwriter.utils.template import *
import typing as t
from collections.abc import Mapping
import moduleb


class OuterScopeVar(Component):
    def __init__(self, thing):
        self.thing = thing
        self.other = 'outer-val'

    template = """
    outer before: thing is <<self.thing>>!
    % r InnerScopeVar(thing='y')
    % /r
    outer after: thing is still <<self.thing>>!"""


class InnerScopeVar(Component):
    def __init__(self, thing):
        self.thing = thing

    template = """
    inner: thing is <<self.thing>>!
    inner: other is <<self.other if hasattr(self, 'other') else 'UNSET'>>"""


class ComponentResolutionSameFileChild(Component):
    template = "hi"


class ComponentResolutionSameFile(Component):
    # simplest possible case of referring to another component defined
    # in the same module/file.
    template = """
    % r ComponentResolutionSameFileChild()
    % /r
    """


class ComponentResolutionSameFileErr(Component):
    # refer to non-existing component
    template = """
    % r DefinitelyNotExistingComponent()
    % /r
    """


class ComponentResolutionViaModule(Component):
    template = """
    % r moduleb.ComponentResolutionViaModuleChild()
    %/r
    """