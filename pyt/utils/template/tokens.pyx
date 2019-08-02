
cdef class Token:
    def __repr__(self):
        return f"({type(self).__name__})"

cdef class CtrlToken(Token):
    def __init__(self, str prefix, str keyword, str args = ""):
        self.prefix = prefix
        self.keyword = keyword
        self.args = args

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.prefix == other.prefix
            and self.keyword == other.keyword
            and self.args == other.args)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f"CtrlToken('{self.prefix}', '{self.keyword}', '{self.args}')"

cdef class ExprToken(Token):
    def __init__(self, str expr):
        self.expr = expr

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.expr == other.expr)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f"ExprToken('{self.expr}')"

cdef class TextToken(Token):
    def __init__(self, str text):
        self.text = text

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.text == other.text)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f"TextToken('{self.text}')"

cdef class NewlineToken(Token):
    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "NewlineToken"