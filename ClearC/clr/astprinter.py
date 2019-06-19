"""
Module defining an ast visitor to pretty print the ast.
"""

from typing import Callable

import clr.ast as ast


class AstPrinter(ast.AstVisitor):
    """
    Ast visitor that pretty prints the nodes it visits.
    """

    def __init__(self, printer: Callable[[str], None] = print) -> None:
        self.indent = 0
        self.printer = printer
        self.buffer = ""

    def flush(self) -> None:
        """
        Flush the buffer.
        """
        self.printer(self.buffer)
        self.buffer = ""

    def append(self, string: str) -> None:
        """
        Append a string to the buffer.
        """
        self.buffer += string

    def startline(self) -> None:
        """
        Starts a new line to print on.
        """
        self.flush()
        self.append("    " * self.indent)

    def value_decl(self, node: ast.AstValueDecl) -> None:
        self.append(f"val {node.ident} ")
        if node.val_type:
            node.val_type.accept(self)
            self.append(" ")
        self.append("= ")
        node.val_init.accept(self)
        self.startline()

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        def print_param(param_type: ast.AstType, param_name: str) -> None:
            param_type.accept(self)
            self.append(f" {param_name}")

        self.append(f"func {node.ident}(")
        if node.params:
            print_param(*node.params[0])
            for param_type, param_name in node.params[1:]:
                self.append(", ")
                print_param(param_type, param_name)
        self.append(") ")
        node.return_type.accept(self)
        self.append(" ")
        node.block.accept(self)
        self.startline()

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        self.append("print")
        if node.expr:
            self.append(" ")
            node.expr.accept(self)
        self.append(";")
        self.startline()

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        self.append("{")
        self.indent += 1

        self.startline()
        for decl in node.decls[:-1]:
            decl.accept(self)
        self.indent -= 1
        node.decls[-1].accept(self)

        self.append("}")

    def if_stmt(self, node: ast.AstIfStmt) -> None:
        def print_part(cond: ast.AstExpr, block: ast.AstBlockStmt) -> None:
            self.append("(")
            cond.accept(self)
            self.append(") ")
            block.accept(self)

        self.append("if ")
        print_part(*node.if_part)
        for cond, block in node.elif_parts:
            self.append(" else if ")
            print_part(cond, block)
        if node.else_part:
            self.append(" else ")
            node.else_part.accept(self)
        self.startline()

    def while_stmt(self, node: ast.AstWhileStmt) -> None:
        self.append("while ")
        if node.cond:
            self.append("(")
            node.cond.accept(self)
            self.append(") ")
        node.block.accept(self)
        self.startline()

    def return_stmt(self, node: ast.AstReturnStmt) -> None:
        self.append("return")
        if node.expr:
            self.append(" ")
            node.expr.accept(self)
        self.append(";")
        self.startline()

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        node.expr.accept(self)
        self.append(";")
        self.startline()

    def unary_expr(self, node: ast.AstUnaryExpr) -> None:
        self.append(f"{node.operator}(")
        node.target.accept(self)
        self.append(")")

    def binary_expr(self, node: ast.AstBinaryExpr) -> None:
        self.append("(")
        node.left.accept(self)
        self.append(f"){node.operator}(")
        node.right.accept(self)
        self.append(")")

    def int_expr(self, node: ast.AstIntExpr) -> None:
        self.append(node.literal)

    def num_expr(self, node: ast.AstNumExpr) -> None:
        self.append(node.literal)

    def str_expr(self, node: ast.AstStrExpr) -> None:
        self.append(node.literal)

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        self.append(node.name)

    def call_expr(self, node: ast.AstCallExpr) -> None:
        node.function.accept(self)
        self.append("(")
        if node.args:
            node.args[0].accept(self)
            for arg in node.args[1:]:
                self.append(", ")
                arg.accept(self)
        self.append(")")

    def atom_type(self, node: ast.AstAtomType) -> None:
        self.append(node.token)

    def func_type(self, node: ast.AstFuncType) -> None:
        self.append("func")
        self.append("(")
        if node.params:
            node.params[0].accept(self)
            for param in node.params[1:]:
                self.append(", ")
                param.accept(self)
        self.append(") ")
        node.return_type.accept(self)

    def optional_type(self, node: ast.AstOptionalType) -> None:
        self.append("(")
        node.target.accept(self)
        self.append(")?")


def pprint(node: ast.AstNode) -> None:
    """
    Pretty prints a given ast node.
    """
    node.accept(AstPrinter())
