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


TYPE_VOID = ast.BuiltinTypeAnnot("void")
TYPE_STR = ast.BuiltinTypeAnnot("str")
TYPE_BOOL = ast.BuiltinTypeAnnot("bool")
TYPE_INT = ast.BuiltinTypeAnnot("int")
TYPE_NUM = ast.BuiltinTypeAnnot("num")

ARITH_TYPES = [TYPE_INT, TYPE_NUM]
ARITH_UNARY = ["-"]
ARITH_BINARY = ["+", "-", "*", "/"]


def valid(type_annot: ast.TypeAnnot) -> bool:
    """
    Checks if a type annotation is a valid type for a value to have.
    """
    if isinstance(type_annot, ast.BuiltinTypeAnnot):
        return type_annot in [TYPE_STR, TYPE_BOOL, TYPE_INT, TYPE_NUM]
    if isinstance(type_annot, ast.FuncTypeAnnot):
        return all(valid(param) for param in type_annot.params) and (
            valid(type_annot.return_type) or type_annot.return_type == TYPE_VOID
        )
    if isinstance(type_annot, ast.OptionalTypeAnnot):
        return valid(type_annot.target)
    return False


class TypeChecker(ast.DeepVisitor):
    """
    Ast visitor to annotate and check types.
    """

    def __init__(self) -> None:
        self.errors = lexer.ErrorTracker()

    def value_decl(self, node: ast.AstValueDecl) -> None:
        super().value_decl(node)
        if node.val_type:
            if not valid(node.val_type.type_annot):
                self.errors.add(
                    message=f"invalid value type {node.val_type}",
                    region=node.val_type.region,
                )
            node.type_annot = node.val_type.type_annot
            # TODO: Handle optional/nil better, not just equality checks
            if node.type_annot != node.val_init.type_annot:
                self.errors.add(
                    message=f"mismatched type for value initializer: expected {node.type_annot} but got {node.val_init.type_annot}",
                    region=node.val_init.region,
                )
        else:
            node.type_annot = node.val_init.type_annot
            if node.type_annot == TYPE_VOID:
                self.errors.add(
                    message="cannot declare value as void", region=node.val_init.region
                )

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        super().func_decl(node)
        if (
            not valid(node.return_type.type_annot)
            and node.return_type.type_annot != TYPE_VOID
        ):
            self.errors.add(
                message=f"invalid return type {node.return_type.type_annot}",
                region=node.return_type.region,
            )
        node.type_annot = ast.FuncTypeAnnot(
            [param.type_annot for param in node.params], node.return_type.type_annot
        )

    def param(self, node: ast.AstParam) -> None:
        super().param(node)
        node.type_annot = node.param_type.type_annot
        if not valid(node.type_annot):
            self.errors.add(
                message=f"invalid type {node.type_annot} for parameter",
                region=node.region,
            )

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        super().print_stmt(node)
        if node.expr and node.expr.type_annot != TYPE_STR:
            self.errors.add(
                message=f"invalid type {node.expr.type_annot} to print, expected str",
                region=node.expr.region,
            )

    def _check_cond(self, cond: ast.AstExpr) -> None:
        if cond.type_annot != TYPE_BOOL:
            self.errors.add(
                message=f"invalid type {cond.type_annot} for condition, expected bool",
                region=cond.region,
            )

    def if_stmt(self, node: ast.AstIfStmt) -> None:
        super().if_stmt(node)
        self._check_cond(node.if_part[0])
        for cond, _ in node.elif_parts:
            self._check_cond(cond)

    def while_stmt(self, node: ast.AstWhileStmt) -> None:
        super().while_stmt(node)
        if node.cond:
            self._check_cond(node.cond)

    def return_stmt(self, node: ast.AstReturnStmt) -> None:
        super().return_stmt(node)
        # TODO: check against expected return type, probably with extra passes before this
        if node.expr and not valid(node.expr.type_annot):
            self.errors.add(
                message=f"invalid type {node.expr.type_annot} to return",
                region=node.expr.region,
            )

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        super().expr_stmt(node)
        if not valid(node.expr.type_annot) and node.expr.type_annot != TYPE_VOID:
            self.errors.add(
                f"invalid expression type {node.expr.type_annot}",
                region=node.expr.region,
            )

    def unary_expr(self, node: ast.AstUnaryExpr) -> None:
        super().unary_expr(node)
        if str(node.operator) in ARITH_UNARY:
            if node.target.type_annot not in ARITH_TYPES:
                self.errors.add(
                    message=f"invalid type {node.target.type_annot} for unary operator {node.operator}",
                    region=node.target.region,
                )
            node.type_annot = node.target.type_annot
        else:
            self.errors.add(
                message=f"unknown unary operator {node.operator}",
                region=node.operator.lexeme,
            )

    def binary_expr(self, node: ast.AstBinaryExpr) -> None:
        super().binary_expr(node)
        if str(node.operator) in ARITH_BINARY:
            if node.left.type_annot != node.right.type_annot:
                self.errors.add(
                    message=f"mismatched types {node.left.type_annot} and {node.right.type_annot} for binary operator {node.operator}",
                    region=node.region,
                )
            else:
                # Overloaded concat operator
                if str(node.operator) == "+" and node.left.type_annot == TYPE_STR:
                    pass
                elif node.left.type_annot not in ARITH_TYPES:
                    self.errors.add(
                        message=f"invalid operand type {node.left.type_annot} for binary operator {node.operator}",
                        region=node.region,
                    )
            node.type_annot = node.left.type_annot
        else:
            self.errors.add(
                message=f"unknown binary operator {node.operator}",
                region=node.operator.lexeme,
            )

    def int_expr(self, node: ast.AstIntExpr) -> None:
        super().int_expr(node)
        node.type_annot = TYPE_INT

    def num_expr(self, node: ast.AstNumExpr) -> None:
        super().num_expr(node)
        node.type_annot = TYPE_NUM

    def str_expr(self, node: ast.AstStrExpr) -> None:
        super().str_expr(node)
        node.type_annot = TYPE_STR

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        super().ident_expr(node)
        if node.ref:
            node.type_annot = node.ref.type_annot
        else:
            self.errors.add(
                message=f"couldn't resolve identifier {node.name}", region=node.region
            )

    def bool_expr(self, node: ast.AstBoolExpr) -> None:
        super().bool_expr(node)
        node.type_annot = TYPE_BOOL

    def call_expr(self, node: ast.AstCallExpr) -> None:
        super().call_expr(node)
        if not isinstance(node.function.type_annot, ast.FuncTypeAnnot):
            self.errors.add(
                message=f"invalid type {node.function.type_annot} to call, expected a function",
                region=node.function.region,
            )
            return
        arg_count = len(node.args)
        param_count = len(node.function.type_annot.params)
        if arg_count != param_count:
            adjective = "few" if arg_count < param_count else "many"
            self.errors.add(
                message=f"too {adjective} arguments to function: expected {param_count} but got {arg_count}",
                region=lexer.SourceView.range(
                    node.args[0].region, node.args[-1].region
                ),
            )
        else:
            for arg, param in zip(node.args, node.function.type_annot.params):
                if arg.type_annot != param:
                    self.errors.add(
                        message=f"mismatched type for argument: expected {param} but got {arg.type_annot}",
                        region=arg.region,
                    )
        node.type_annot = node.function.type_annot.return_type

    def atom_type(self, node: ast.AstAtomType) -> None:
        super().atom_type(node)
        node.type_annot = ast.BuiltinTypeAnnot(node.name)
        if not valid(node.type_annot) and node.type_annot != TYPE_VOID:
            self.errors.add(
                message=f"invalid type {node.type_annot}", region=node.region
            )

    def func_type(self, node: ast.AstFuncType) -> None:
        super().func_type(node)
        node.type_annot = ast.FuncTypeAnnot(
            [param.type_annot for param in node.params], node.return_type.type_annot
        )
        if not valid(node.type_annot):
            self.errors.add(
                message=f"invalid type {node.type_annot}", region=node.region
            )

    def optional_type(self, node: ast.AstOptionalType) -> None:
        super().optional_type(node)
        node.type_annot = ast.OptionalTypeAnnot(node.target.type_annot)
        if not valid(node.type_annot):
            self.errors.add(
                message=f"invalid type {node.type_annot}", region=node.region
            )
