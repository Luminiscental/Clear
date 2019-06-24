"""
Module defining an ast visitor to type check.
"""

from typing import List, Optional, Callable, TypeVar

import clr.errors as er
import clr.ast as ast
import clr.annotations as an

T = TypeVar("T")  # pylint: disable=invalid-name
R = TypeVar("R")  # pylint: disable=invalid-name

ARITH_UNARY = ["-"]
ARITH_BINARY = ["+", "-", "*", "/"]

COMP_BINARY = ["==", "!="]


def guess_arith_binary(lhs: an.TypeAnnot, rhs: an.TypeAnnot) -> an.TypeAnnot:
    """
    Guess the result type of an arithmetic binary operator given mismatched lhs and rhs types.
    """
    # If there's a str assume user wanted concatenation
    if an.BuiltinTypeAnnot.STR in (lhs, rhs):
        return an.BuiltinTypeAnnot.STR
    # If there's a num assume user wanted num operation
    if an.BuiltinTypeAnnot.NUM in (lhs, rhs):
        return an.BuiltinTypeAnnot.NUM
    # Fallback to int
    return an.BuiltinTypeAnnot.INT


def symmetrize(func: Callable[[T, T], Optional[R]]) -> Callable[[T, T], Optional[R]]:
    """
    Makes a function attempt both orders of arguments before returning None.
    """

    def result(lhs: T, rhs: T) -> Optional[R]:
        return func(lhs, rhs) or func(rhs, lhs)

    return result


@symmetrize
def union(lhs: an.TypeAnnot, rhs: an.TypeAnnot) -> Optional[an.TypeAnnot]:
    """
    Returns the type that contains both the lhs and rhs type, if it exists.
    """
    if lhs == rhs:
        return lhs
    if lhs == an.BuiltinTypeAnnot.NIL:
        if isinstance(rhs, an.OptionalTypeAnnot):
            return rhs
        return an.OptionalTypeAnnot(rhs)
    if isinstance(lhs, an.OptionalTypeAnnot) and rhs == lhs.target:
        return lhs
    return None


def contains(inner: an.TypeAnnot, outer: an.TypeAnnot) -> bool:
    """
    Checks if the inner type is contained by the outer type (defers to union).
    """
    combined = union(outer, inner)
    if combined is None:
        return False
    return combined == outer


def valid(type_annot: an.TypeAnnot) -> bool:
    """
    Checks if a type annotation is a valid type for a value to have.
    """
    if isinstance(type_annot, an.BuiltinTypeAnnot):
        return True
    if isinstance(type_annot, an.FuncTypeAnnot):
        return all(valid(param) for param in type_annot.params) and (
            valid(type_annot.return_type)
            or type_annot.return_type == an.BuiltinTypeAnnot.VOID
        )
    if isinstance(type_annot, an.OptionalTypeAnnot):
        return valid(type_annot.target)
    return False


class TypeChecker(ast.DeepVisitor):
    """
    Ast visitor to annotate and check types.
    """

    def __init__(self) -> None:
        super().__init__()
        self.expected_returns: List[an.TypeAnnot] = []

    def value_decl(self, node: ast.AstValueDecl) -> None:
        super().value_decl(node)
        if node.val_type:
            if not valid(node.val_type.type_annot):
                self.errors.add(
                    message=f"invalid value type {node.val_type}",
                    regions=[node.val_type.region],
                )
            node.type_annot = node.val_type.type_annot
            if not contains(node.val_init.type_annot, node.type_annot):
                self.errors.add(
                    message=f"mismatched type for value initializer: "
                    f"expected {node.type_annot} but got {node.val_init.type_annot}",
                    regions=[node.val_init.region],
                )
        else:
            node.type_annot = node.val_init.type_annot
            if node.type_annot == an.BuiltinTypeAnnot.VOID:
                self.errors.add(
                    message="cannot declare value as void",
                    regions=[node.val_init.region],
                )

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        for param in node.params:
            param.accept(self)
        node.return_type.accept(self)
        if (
            not valid(node.return_type.type_annot)
            and node.return_type.type_annot != an.BuiltinTypeAnnot.VOID
        ):
            self.errors.add(
                message=f"invalid return type {node.return_type.type_annot}",
                regions=[node.return_type.region],
            )
        node.type_annot = an.FuncTypeAnnot(
            [param.type_annot for param in node.params], node.return_type.type_annot
        )
        self.expected_returns.append(node.type_annot.return_type)
        node.block.accept(self)
        self.expected_returns.pop()

    def param(self, node: ast.AstParam) -> None:
        super().param(node)
        node.type_annot = node.param_type.type_annot
        if not valid(node.type_annot):
            self.errors.add(
                message=f"invalid type {node.type_annot} for parameter",
                regions=[node.region],
            )

    def _check_cond(self, cond: ast.AstExpr) -> None:
        if cond.type_annot != an.BuiltinTypeAnnot.BOOL:
            self.errors.add(
                message=f"invalid type {cond.type_annot} for condition, expected bool",
                regions=[cond.region],
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
        if not self.expected_returns:
            self.errors.add(
                message=f"return statement outside of function", regions=[node.region]
            )
        if node.expr:
            if not valid(node.expr.type_annot):
                self.errors.add(
                    message=f"invalid type {node.expr.type_annot} to return",
                    regions=[node.expr.region],
                )
            elif not contains(node.expr.type_annot, self.expected_returns[-1]):
                self.errors.add(
                    message=f"mismatched return type: "
                    f"expected {self.expected_returns[-1]} but got {node.expr.type_annot}",
                    regions=[node.expr.region],
                )
        else:
            if self.expected_returns[-1] != an.BuiltinTypeAnnot.VOID:
                self.errors.add(
                    message=f"missing return value in non-void function",
                    regions=[node.region],
                )

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        super().expr_stmt(node)
        if (
            not valid(node.expr.type_annot)
            and node.expr.type_annot != an.BuiltinTypeAnnot.VOID
        ):
            self.errors.add(
                f"invalid expression type {node.expr.type_annot}",
                regions=[node.expr.region],
            )
        if node.expr.type_annot != an.BuiltinTypeAnnot.VOID:
            self.errors.add(
                message=f"unused non-void value",
                regions=[node.expr.region],
                severity=er.Severity.WARNING,
            )

    def unary_expr(self, node: ast.AstUnaryExpr) -> None:
        super().unary_expr(node)
        if str(node.operator) in ARITH_UNARY:
            if node.target.type_annot not in an.ARITH_TYPES:
                self.errors.add(
                    message=f"invalid type {node.target.type_annot} "
                    f"for unary operator {node.operator}",
                    regions=[node.target.region],
                )
            node.type_annot = node.target.type_annot
        else:
            self.errors.add(
                message=f"unknown unary operator {node.operator}",
                regions=[node.operator.lexeme],
            )

    def binary_expr(self, node: ast.AstBinaryExpr) -> None:
        super().binary_expr(node)
        if str(node.operator) in ARITH_BINARY:
            if node.left.type_annot != node.right.type_annot:
                self.errors.add(
                    message=f"mismatched types {node.left.type_annot} and {node.right.type_annot} "
                    f"for binary operator {node.operator}",
                    regions=[node.region],
                )
                # Guess the result type for smoother chain er
                node.type_annot = guess_arith_binary(
                    node.left.type_annot, node.right.type_annot
                )
            else:
                # Overloaded concat operator
                if (
                    str(node.operator) == "+"
                    and node.left.type_annot == an.BuiltinTypeAnnot.STR
                ):
                    pass
                elif node.left.type_annot not in an.ARITH_TYPES:
                    self.errors.add(
                        message=f"invalid operand type {node.left.type_annot} "
                        f"for binary operator {node.operator}",
                        regions=[node.region],
                    )
                node.type_annot = node.left.type_annot
        elif str(node.operator) in COMP_BINARY:

            def check(side: ast.AstExpr) -> None:
                if not valid(side.type_annot):
                    self.errors.add(
                        message=f"invalid type {side.type_annot} "
                        f"for comparison operator {node.operator}",
                        regions=[side.region],
                    )

            check(node.left)
            check(node.right)
            node.type_annot = an.BuiltinTypeAnnot.BOOL
        else:
            self.errors.add(
                message=f"unknown binary operator {node.operator}",
                regions=[node.operator.lexeme],
            )

    def int_expr(self, node: ast.AstIntExpr) -> None:
        super().int_expr(node)
        node.type_annot = an.BuiltinTypeAnnot.INT

    def num_expr(self, node: ast.AstNumExpr) -> None:
        super().num_expr(node)
        node.type_annot = an.BuiltinTypeAnnot.NUM

    def str_expr(self, node: ast.AstStrExpr) -> None:
        super().str_expr(node)
        node.type_annot = an.BuiltinTypeAnnot.STR

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        super().ident_expr(node)
        if node.ref:
            node.type_annot = node.ref.type_annot
        else:
            self.errors.add(
                message=f"couldn't resolve identifier {node.name}",
                regions=[node.region],
            )

    def bool_expr(self, node: ast.AstBoolExpr) -> None:
        super().bool_expr(node)
        node.type_annot = an.BuiltinTypeAnnot.BOOL

    def nil_expr(self, node: ast.AstNilExpr) -> None:
        super().nil_expr(node)
        node.type_annot = an.BuiltinTypeAnnot.NIL

    def call_expr(self, node: ast.AstCallExpr) -> None:
        super().call_expr(node)
        if not isinstance(node.function.type_annot, an.FuncTypeAnnot):
            self.errors.add(
                message=f"invalid type {node.function.type_annot} to call, expected a function",
                regions=[node.function.region],
            )
            return
        arg_count = len(node.args)
        param_count = len(node.function.type_annot.params)
        if arg_count != param_count:
            adjective = "few" if arg_count < param_count else "many"
            self.errors.add(
                message=f"too {adjective} arguments to function: "
                f"expected {param_count} but got {arg_count}",
                regions=[
                    er.SourceView.range(node.args[0].region, node.args[-1].region)
                ],
            )
        else:
            for arg, param in zip(node.args, node.function.type_annot.params):
                if arg.type_annot != param:
                    self.errors.add(
                        message=f"mismatched type for argument: "
                        f"expected {param} but got {arg.type_annot}",
                        regions=[arg.region],
                    )
        node.type_annot = node.function.type_annot.return_type

    def atom_type(self, node: ast.AstAtomType) -> None:
        super().atom_type(node)
        node.type_annot = an.BuiltinTypeAnnot(node.name)
        if not valid(node.type_annot) and node.type_annot != an.BuiltinTypeAnnot.VOID:
            self.errors.add(
                message=f"invalid type {node.type_annot}", regions=[node.region]
            )

    def func_type(self, node: ast.AstFuncType) -> None:
        super().func_type(node)
        node.type_annot = an.FuncTypeAnnot(
            [param.type_annot for param in node.params], node.return_type.type_annot
        )
        if not valid(node.type_annot):
            self.errors.add(
                message=f"invalid type {node.type_annot}", regions=[node.region]
            )

    def optional_type(self, node: ast.AstOptionalType) -> None:
        super().optional_type(node)
        node.type_annot = an.OptionalTypeAnnot(node.target.type_annot)
        if not valid(node.type_annot):
            self.errors.add(
                message=f"invalid type {node.type_annot}", regions=[node.region]
            )
