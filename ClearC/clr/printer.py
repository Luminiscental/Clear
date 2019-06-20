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

    def _flush(self) -> None:
        """
        Flush the buffer.
        """
        self.printer(self.buffer)
        self.buffer = ""

    def _append(self, string: str) -> None:
        """
        Append a string to the buffer.
        """
        self.buffer += string

    def _startline(self) -> None:
        """
        Starts a new line to print on.
        """
        self._flush()
        self._append("    " * self.indent)

    def value_decl(self, node: ast.AstValueDecl) -> None:
        self._append(f"val {node.ident} ")
        if node.val_type:
            node.val_type.accept(self)
            self._append(" ")
        self._append("= ")
        node.val_init.accept(self)
        self._append(";")
        self._startline()

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        self._append(f"func {node.ident}(")
        if node.params:
            node.params[0].accept(self)
            for param in node.params[1:]:
                self._append(", ")
                param.accept(self)
        self._append(") ")
        node.return_type.accept(self)
        self._append(" ")
        node.block.accept(self)
        self._startline()

    def param(self, node: ast.AstParam) -> None:
        node.param_type.accept(self)
        self._append(f" {node.param_name}")

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        self._append("print")
        if node.expr:
            self._append(" ")
            node.expr.accept(self)
        self._append(";")
        self._startline()

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        self._append("{")
        self.indent += 1

        self._startline()
        for decl in node.decls[:-1]:
            decl.accept(self)
        self.indent -= 1
        node.decls[-1].accept(self)

        self._append("}")

    def if_stmt(self, node: ast.AstIfStmt) -> None:
        def print_part(cond: ast.AstExpr, block: ast.AstBlockStmt) -> None:
            self._append("(")
            cond.accept(self)
            self._append(") ")
            block.accept(self)

        self._append("if ")
        print_part(*node.if_part)
        for cond, block in node.elif_parts:
            self._append(" else if ")
            print_part(cond, block)
        if node.else_part:
            self._append(" else ")
            node.else_part.accept(self)
        self._startline()

    def while_stmt(self, node: ast.AstWhileStmt) -> None:
        self._append("while ")
        if node.cond:
            self._append("(")
            node.cond.accept(self)
            self._append(") ")
        node.block.accept(self)
        self._startline()

    def return_stmt(self, node: ast.AstReturnStmt) -> None:
        self._append("return")
        if node.expr:
            self._append(" ")
            node.expr.accept(self)
        self._append(";")
        self._startline()

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        node.expr.accept(self)
        self._append(";")
        self._startline()

    def unary_expr(self, node: ast.AstUnaryExpr) -> None:
        self._append(f"{node.operator}(")
        node.target.accept(self)
        self._append(")")

    def binary_expr(self, node: ast.AstBinaryExpr) -> None:
        self._append("(")
        node.left.accept(self)
        self._append(f"){node.operator}(")
        node.right.accept(self)
        self._append(")")

    def int_expr(self, node: ast.AstIntExpr) -> None:
        self._append(node.literal)

    def num_expr(self, node: ast.AstNumExpr) -> None:
        self._append(node.literal)

    def str_expr(self, node: ast.AstStrExpr) -> None:
        self._append(node.literal)

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        self._append(node.name)

    def bool_expr(self, node: ast.AstBoolExpr) -> None:
        self._append("true" if node.value else "false")

    def call_expr(self, node: ast.AstCallExpr) -> None:
        node.function.accept(self)
        self._append("(")
        if node.args:
            node.args[0].accept(self)
            for arg in node.args[1:]:
                self._append(", ")
                arg.accept(self)
        self._append(")")

    def atom_type(self, node: ast.AstAtomType) -> None:
        self._append(node.token)

    def func_type(self, node: ast.AstFuncType) -> None:
        self._append("func")
        self._append("(")
        if node.params:
            node.params[0].accept(self)
            for param in node.params[1:]:
                self._append(", ")
                param.accept(self)
        self._append(") ")
        node.return_type.accept(self)

    def optional_type(self, node: ast.AstOptionalType) -> None:
        self._append("(")
        node.target.accept(self)
        self._append(")?")


def pprint(node: ast.AstNode) -> None:
    """
    Pretty prints a given ast node.
    """
    node.accept(AstPrinter())
