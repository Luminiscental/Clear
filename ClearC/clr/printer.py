"""
Module defining an ast visitor to pretty print the ast.
"""

from typing import Callable

import clr.ast as ast


def pprint(node: ast.AstNode) -> None:
    """
    Pretty prints a given ast node.
    """
    printer = AstPrinter()
    node.accept(printer)
    printer.flush()


class AstPrinter(ast.AstVisitor):
    """
    Ast visitor that pretty prints the nodes it visits.
    """

    def __init__(self, printer: Callable[[str], None] = print) -> None:
        self._indent = 0
        self._printer = printer
        self._buffer = ""
        self._dont_break = False

    def flush(self) -> None:
        """
        Flush the buffer if it isn't empty.
        """
        if self._buffer:
            self._printer(self._buffer)
            self._buffer = ""

    def _append(self, string: str) -> None:
        self._buffer += string

    def _startline(self) -> None:
        if self._dont_break:
            self._dont_break = False
        else:
            if self._buffer:
                self.flush()
            self._append("    " * self._indent)

    def value_decl(self, node: ast.AstValueDecl) -> None:
        self._startline()
        self._append(f"val {node.ident} ")
        if node.val_type:
            node.val_type.accept(self)
            self._append(" ")
        self._append("= ")
        node.val_init.accept(self)
        self._append(";")

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        self._startline()
        self._append(f"func {node.ident}(")
        if node.params:
            node.params[0].accept(self)
            for param in node.params[1:]:
                self._append(", ")
                param.accept(self)
        self._append(") ")
        node.return_type.accept(self)
        self._append(" ")
        self._dont_break = True
        node.block.accept(self)

    def param(self, node: ast.AstParam) -> None:
        node.param_type.accept(self)
        self._append(f" {node.param_name}")

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        self._startline()
        self._append("print")
        if node.expr:
            self._append(" ")
            node.expr.accept(self)
        self._append(";")

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        self._startline()
        self._append("{")
        self._indent += 1
        for decl in node.decls:
            decl.accept(self)
        self._indent -= 1
        self._startline()
        self._append("}")

    def if_stmt(self, node: ast.AstIfStmt) -> None:
        def print_part(cond: ast.AstExpr, block: ast.AstBlockStmt) -> None:
            self._append("(")
            cond.accept(self)
            self._append(") ")
            self._dont_break = True
            block.accept(self)

        self._startline()
        self._append("if ")
        print_part(*node.if_part)
        for cond, block in node.elif_parts:
            self._append(" else if ")
            print_part(cond, block)
        if node.else_part:
            self._append(" else ")
            self._dont_break = True
            node.else_part.accept(self)

    def while_stmt(self, node: ast.AstWhileStmt) -> None:
        self._startline()
        self._append("while ")
        if node.cond:
            self._append("(")
            node.cond.accept(self)
            self._append(") ")
        self._dont_break = True
        node.block.accept(self)

    def return_stmt(self, node: ast.AstReturnStmt) -> None:
        self._startline()
        self._append("return")
        if node.expr:
            self._append(" ")
            node.expr.accept(self)
        self._append(";")

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        self._startline()
        node.expr.accept(self)
        self._append(";")

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
        self._append(node.name)

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
