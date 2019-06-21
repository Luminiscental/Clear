"""
Module defining an ast visitor to type check.
"""

from typing import List

import clr.lexer as lexer
import clr.ast as ast


def check_types(tree: ast.Ast) -> List[lexer.CompileError]:
    """
    Run the type checker over an ast.
    """
    checker = TypeChecker()
    tree.accept(checker)
    return checker.errors.get()


ARITH_TYPES = [ast.BuiltinTypeAnnot("num"), ast.BuiltinTypeAnnot("int")]
ARITH_UNARY = ["-"]
ARITH_BINARY = ["+", "-", "*", "/"]


class TypeChecker(ast.DeepVisitor):
    """
    Ast visitor to annotate and check types.
    """

    def __init__(self) -> None:
        self.errors = lexer.ErrorTracker()

    def _check_value_type(self, type_annot: ast.TypeAnnot) -> None:
        if isinstance(type_annot, ast.FuncTypeAnnot):
            for param in type_annot.params:
                self._check_value_type(param)
            # return_type can be void so not checked
        elif isinstance(type_annot, ast.BuiltinTypeAnnot):
            if type_annot.name not in ["int", "num", "str", "bool"]:
                self.errors.add(
                    message=f"invalid type {type_annot} for value",
                    region=lexer.SourceView.all(""),
                )
        elif isinstance(type_annot, ast.OptionalTypeAnnot):
            self._check_value_type(type_annot.target)
        elif type_annot is None:
            self.errors.add(
                message=f"unresolved type for value", region=lexer.SourceView.all("")
            )
        else:
            self.errors.add(
                message=f"unknown type {type_annot}", region=lexer.SourceView.all("")
            )

    def value_decl(self, node: ast.AstValueDecl) -> None:
        super().value_decl(node)
        # Propogate
        if node.val_type:
            node.type_annot = node.val_type.type_annot
        else:
            node.type_annot = node.val_init.type_annot
        # Check
        self._check_value_type(node.type_annot)
        # TODO: Handle optional/nil better, not just equality checks
        if node.type_annot != node.val_init.type_annot:
            self.errors.add(
                message=f"mismatched types for value declaration: "
                f"expected {node.type_annot} but got {node.val_init.type_annot}",
                region=lexer.SourceView.all(""),
            )

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        super().func_decl(node)
        # Propogate
        node.type_annot = ast.FuncTypeAnnot(
            [param.type_annot for param in node.params], node.return_type.type_annot
        )
        # Check
        # TODO: Check return statements, probably do stuff in more passes before this
        self._check_value_type(node.type_annot)

    def param(self, node: ast.AstParam) -> None:
        super().param(node)
        # Propogate
        node.type_annot = node.param_type.type_annot
        # Check
        self._check_value_type(node.type_annot)

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        super().print_stmt(node)
        if node.expr:
            print(f"printing {node.expr.type_annot}")
        # Check
        if node.expr and node.expr.type_annot != ast.BuiltinTypeAnnot("str"):
            self.errors.add(
                message=f"invalid type {node.expr.type_annot} to print, expected str",
                region=lexer.SourceView.all(""),
            )

    def if_stmt(self, node: ast.AstIfStmt) -> None:
        super().if_stmt(node)
        # Check
        if node.if_part[0].type_annot != ast.BuiltinTypeAnnot("bool"):
            self.errors.add(
                message=f"invalid type {node.if_part[0].type_annot} for condition, expected bool",
                region=lexer.SourceView.all(""),
            )
        for cond, _ in node.elif_parts:
            if cond.type_annot != ast.BuiltinTypeAnnot("bool"):
                self.errors.add(
                    message=f"invalid type {cond.type_annot} for condition, expected bool",
                    region=lexer.SourceView.all(""),
                )

    def while_stmt(self, node: ast.AstWhileStmt) -> None:
        super().while_stmt(node)
        # Check
        if node.cond and node.cond.type_annot != ast.BuiltinTypeAnnot("bool"):
            self.errors.add(
                message=f"invalid type {node.cond.type_annot} for condition, expected bool",
                region=lexer.SourceView.all(""),
            )

    def return_stmt(self, node: ast.AstReturnStmt) -> None:
        super().return_stmt(node)
        # TODO: check against expected return type
        # Check
        if node.expr:
            self._check_value_type(node.expr.type_annot)

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        super().expr_stmt(node)
        # Allow void expression

    def unary_expr(self, node: ast.AstUnaryExpr) -> None:
        super().unary_expr(node)
        if node.operator in ARITH_UNARY:
            # Propogate
            node.type_annot = node.target.type_annot
            # Check
            if node.target.type_annot not in ARITH_TYPES:
                self.errors.add(
                    message=f"invalid type {node.target.type_annot} for unary operator {node.operator}",
                    region=lexer.SourceView.all(""),
                )
        else:
            self.errors.add(
                message=f"unknown unary operator {node.operator}",
                region=lexer.SourceView.all(""),
            )

    def binary_expr(self, node: ast.AstBinaryExpr) -> None:
        super().binary_expr(node)
        if node.operator in ARITH_BINARY:
            # Propogate
            node.type_annot = node.left.type_annot
            # Check
            if node.left.type_annot != node.right.type_annot:
                self.errors.add(
                    message=f"mismatched types for binary operator {node.operator}: "
                    f"lhs is {node.left.type_annot} but rhs is {node.right.type_annot}",
                    region=lexer.SourceView.all(""),
                )
            if node.left.type_annot not in ARITH_TYPES:
                self.errors.add(
                    message=f"invalid type {node.left.type_annot} for binary operator {node.operator}",
                    region=lexer.SourceView.all(""),
                )
        else:
            self.errors.add(
                message=f"unknown binary operator {node.operator}",
                region=lexer.SourceView.all(""),
            )

    def int_expr(self, node: ast.AstIntExpr) -> None:
        super().int_expr(node)
        # Propogate
        node.type_annot = ast.BuiltinTypeAnnot("int")

    def num_expr(self, node: ast.AstNumExpr) -> None:
        super().num_expr(node)
        # Propogate
        node.type_annot = ast.BuiltinTypeAnnot("num")

    def str_expr(self, node: ast.AstStrExpr) -> None:
        super().str_expr(node)
        # Propogate
        node.type_annot = ast.BuiltinTypeAnnot("str")

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        super().ident_expr(node)
        # Check
        if not node.ref:
            self.errors.add(
                message=f"couldn't resolve identifier {node.name}",
                region=lexer.SourceView.all(""),
            )
            return
        self._check_value_type(node.ref.type_annot)
        # Propogate
        node.type_annot = node.ref.type_annot

    def bool_expr(self, node: ast.AstBoolExpr) -> None:
        super().bool_expr(node)
        # Propogate
        node.type_annot = ast.BuiltinTypeAnnot("bool")

    def call_expr(self, node: ast.AstCallExpr) -> None:
        super().call_expr(node)
        # Check
        if not isinstance(node.function.type_annot, ast.FuncTypeAnnot):
            self.errors.add(
                message=f"invalid type {node.function.type_annot} to call, expected a function",
                region=lexer.SourceView.all(""),
            )
            return
        arg_count = len(node.args)
        param_count = len(node.function.type_annot.params)
        if arg_count > param_count:
            self.errors.add(
                message=f"too many arguments to function: "
                f"expected {param_count} but got {arg_count}",
                region=lexer.SourceView.all(""),
            )
        elif arg_count < param_count:
            self.errors.add(
                message=f"too few arguments to function: "
                f"expected {param_count} but got {arg_count}",
                region=lexer.SourceView.all(""),
            )
        else:
            for arg, param in zip(node.args, node.function.type_annot.params):
                if arg.type_annot != param:
                    self.errors.add(
                        message=f"mismatched type for argument: "
                        f"expected {param} but got {arg.type_annot}",
                        region=lexer.SourceView.all(""),
                    )
        # Allow void expression
        # Propogate
        node.type_annot = node.function.type_annot.return_type

    def atom_type(self, node: ast.AstAtomType) -> None:
        super().atom_type(node)
        # Propogate
        node.type_annot = ast.BuiltinTypeAnnot(node.name)

    def func_type(self, node: ast.AstFuncType) -> None:
        super().func_type(node)
        # Propogate
        node.type_annot = ast.FuncTypeAnnot(
            [param.type_annot for param in node.params], node.return_type.type_annot
        )

    def optional_type(self, node: ast.AstOptionalType) -> None:
        super().optional_type(node)
        node.type_annot = ast.OptionalTypeAnnot(node.target.type_annot)
