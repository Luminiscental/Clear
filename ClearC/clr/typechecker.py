"""
Module defining an ast visitor to type check.
"""

from typing import Set, List, Callable, Dict, Tuple

import clr.errors as er
import clr.ast as ast
import clr.annotations as an


def contract_union(types: Set[an.UnitType]) -> an.TypeAnnot:
    """
    Contracts an expanded list of types into a single type annotation.
    """
    # Unresolved types contaminate the whole union
    if an.UnresolvedTypeAnnot() in types:
        return an.UnresolvedTypeAnnot()
    # If there's only one type the union is trivial
    if len(types) == 1:
        return types.pop()
    # Nil makes the union optional
    if an.BuiltinTypeAnnot.NIL in types:
        target = contract_union(
            {subtype for subtype in types if subtype != an.BuiltinTypeAnnot.NIL}
        )
        return an.OptionalTypeAnnot(target)
    # Otherwise make a union type
    return an.UnionTypeAnnot({subtype for subtype in types})


def union(lhs: an.TypeAnnot, rhs: an.TypeAnnot) -> an.TypeAnnot:
    """
    Returns the simplest type containing both the lhs and rhs.
    """
    return contract_union(lhs.expand().union(rhs.expand()))


def contains(inner: an.TypeAnnot, outer: an.TypeAnnot) -> bool:
    """
    Checks if the inner type is contained by the outer type (defers to union).
    """
    return union(outer, inner) == contract_union(outer.expand())


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
    if isinstance(type_annot, an.UnionTypeAnnot):
        if not type_annot.types:
            return False
        return all(map(valid, type_annot.types))
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

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        super().print_stmt(node)
        printable_types = an.UnionTypeAnnot(
            {
                value
                for value in an.BuiltinTypeAnnot
                if value != an.BuiltinTypeAnnot.VOID
            }
        )
        if node.expr and not contains(node.expr.type_annot, printable_types):
            self.errors.add(
                message=f"unprintable type {node.expr.type_annot}",
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
        unary_ops = {"-": [an.BuiltinTypeAnnot.NUM, an.BuiltinTypeAnnot.INT]}
        operator = str(node.operator)
        if operator in unary_ops:
            if node.target.type_annot not in unary_ops[operator]:
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
        typed_binary_ops: Dict[
            str, Tuple[an.TypeAnnot, Callable[[an.TypeAnnot], an.TypeAnnot]]
        ] = {
            "+": (
                an.UnionTypeAnnot(
                    {
                        an.BuiltinTypeAnnot.NUM,
                        an.BuiltinTypeAnnot.INT,
                        an.BuiltinTypeAnnot.STR,
                    }
                ),
                lambda in_type: in_type,
            ),
            "-": (
                an.UnionTypeAnnot({an.BuiltinTypeAnnot.NUM, an.BuiltinTypeAnnot.INT}),
                lambda in_type: in_type,
            ),
            "*": (
                an.UnionTypeAnnot({an.BuiltinTypeAnnot.NUM, an.BuiltinTypeAnnot.INT}),
                lambda in_type: in_type,
            ),
            "/": (
                an.UnionTypeAnnot({an.BuiltinTypeAnnot.NUM, an.BuiltinTypeAnnot.INT}),
                lambda in_type: in_type,
            ),
            "<": (
                an.UnionTypeAnnot({an.BuiltinTypeAnnot.NUM, an.BuiltinTypeAnnot.INT}),
                lambda _: an.BuiltinTypeAnnot.BOOL,
            ),
            ">": (
                an.UnionTypeAnnot({an.BuiltinTypeAnnot.NUM, an.BuiltinTypeAnnot.INT}),
                lambda _: an.BuiltinTypeAnnot.BOOL,
            ),
            "<=": (
                an.UnionTypeAnnot({an.BuiltinTypeAnnot.NUM, an.BuiltinTypeAnnot.INT}),
                lambda _: an.BuiltinTypeAnnot.BOOL,
            ),
            ">=": (
                an.UnionTypeAnnot({an.BuiltinTypeAnnot.NUM, an.BuiltinTypeAnnot.INT}),
                lambda _: an.BuiltinTypeAnnot.BOOL,
            ),
        }
        untyped_binary_ops: Dict[str, an.TypeAnnot] = {
            "==": an.BuiltinTypeAnnot.BOOL,
            "!=": an.BuiltinTypeAnnot.BOOL,
        }
        operator = str(node.operator)
        if operator in typed_binary_ops:
            if node.left.type_annot != node.right.type_annot:
                self.errors.add(
                    message=f"mismatched types {node.left.type_annot} and {node.right.type_annot} "
                    f"for binary operator {node.operator}",
                    regions=[node.region],
                )
            else:
                if not contains(node.left.type_annot, typed_binary_ops[operator][0]):
                    self.errors.add(
                        message=f"invalid operand type {node.left.type_annot} "
                        f"for binary operator {node.operator}",
                        regions=[node.region],
                    )
            converter = typed_binary_ops[operator][1]
            node.type_annot = converter(node.left.type_annot)
        elif operator in untyped_binary_ops:
            node.type_annot = untyped_binary_ops[operator]
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
        elif node.name in an.BUILTINS:
            node.type_annot = an.BUILTINS[node.name].type_annot

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
                if not contains(arg.type_annot, param):
                    print(
                        f"arg={arg.type_annot} ; ({repr(arg.type_annot)}), param={param} ; ({repr(param)})"
                    )
                    print(f"union = {union(arg.type_annot, param)}")
                    print(f"contains = {contains(arg.type_annot, param)}")
                    self.errors.add(
                        message=f"mismatched type for argument: "
                        f"expected {param} but got {arg.type_annot}",
                        regions=[arg.region],
                    )
        node.type_annot = node.function.type_annot.return_type

    def atom_type(self, node: ast.AstAtomType) -> None:
        super().atom_type(node)
        try:
            node.type_annot = an.BuiltinTypeAnnot(node.name)
        except ValueError:
            self.errors.add(message=f"invalid type {node.name}", regions=[node.region])

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

    def union_type(self, node: ast.AstUnionType) -> None:
        super().union_type(node)
        node.type_annot = an.UnionTypeAnnot({elem.type_annot for elem in node.types})
        if not valid(node.type_annot) and node.type_annot != an.BuiltinTypeAnnot.VOID:
            self.errors.add(
                message=f"invalid type {node.type_annot}", regions=[node.region]
            )
