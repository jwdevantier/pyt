from ghostwriter.utils.cogen.parser import (
    Program, Block, If, Literal, Expr, Line, CLine
)


class Visitor:

    def visit(self, node):
        return getattr(self,
                       f'visit_{type(node).__name__}',
                       self.default_visitor)(node)

    def default_visitor(self, node):
        raise RuntimeError(f"no visitor for nodes of type '{type(node).__name__}'")


class ASTVisitor(Visitor):
    def visit_Program(self, node: Program):
        return Program([self.visit(l) for l in node.lines])

    def visit_Block(self, node: Block):
        return Block(
            self.visit(node.header),
            [self.visit(l) for l in node.lines]
        )

    def visit_If(self, node: If):
        return If([self.visit(cond) for cond in node.conds])

    def visit_Literal(self, node: Literal):
        return node

    def visit_Expr(self, node: Expr):
        return node

    def visit_Line(self, node: Line):
        return Line([self.visit(n) for n in node.contents])

    def visit_CLine(self, node: CLine):
        return node
