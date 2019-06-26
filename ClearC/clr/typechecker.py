"""
Module defining an ast visitor to type check.
"""

from typing import Set, List, Callable, Dict, Tuple, TypeVar, Iterable

import clr.errors as er
import clr.ast as ast
import clr.annotations as an

T = TypeVar("T")  # pylint: disable=invalid-name
K = TypeVar("K")  # pylint: disable=invalid-name


def _group_by(key_func: Callable[[T], K], values: Iterable[T]) -> Dict[K, Set[T]]:
    grouping: Dict[K, Set[T]] = {}
    for value in values:
        key = key_func(value)
        if key in grouping:
            grouping[key].add(value)
        else:
            grouping[key] = {value}
    return grouping


def _take_functions(
    types: Iterable[an.UnitType]
) -> Tuple[Set[an.FuncTypeAnnot], Set[an.UnitType]]:
    instances = set()
    without: Set[an.UnitType] = set()
    for value in types:
        if isinstance(value, an.FuncTypeAnnot):
            instances.add(value)
        else:
            without.add(value)
    return instances, without


def contract_functions(funcs: Set[an.FuncTypeAnnot]) -> Set[an.FuncTypeAnnot]:
    """
    Contract a set of function types. Any group of functions that take the same number of
    parameters can be combined by intersecting the parameter types and unioning the return types.
    """
    result = set()
    groups = _group_by(lambda func: len(func.params), funcs)
    for param_count, group in groups.items():
        union_return = _union({func.return_type for func in group})
        union_params = [
            _intersection({func.params[i] for func in group})
            for i in range(param_count)
        ]
        result.add(an.FuncTypeAnnot(union_params, union_return))
    return result


def contract_types(types: Set[an.UnitType]) -> an.TypeAnnot:
    """
    Contracts an expanded set of types into a single type annotation.
    """
    # Unresolved types contaminate the whole union
    if an.UnresolvedTypeAnnot() in types:
        return an.UnresolvedTypeAnnot()
    # Take out the functions
    funcs, types = _take_functions(types)
    # Contract them and add back in
    types = types.union(contract_functions(funcs))
    # If there's only one type the union is trivial
    if len(types) == 1:
        return types.pop()
    # Otherwise make a possibly optional union
    target = an.UnionTypeAnnot({subtype for subtype in types if subtype != an.NIL})
    # If there was a nil it's optional
    if an.NIL in types:
        return an.OptionalTypeAnnot(target)
    return target


def _intersection(types: Set[an.TypeAnnot]) -> an.TypeAnnot:
    return contract_types(set.intersection(*[unit.expand() for unit in types]))


def intersection(*args: an.TypeAnnot) -> an.TypeAnnot:
    """
    Returns the simplest type contained in all the args.
    """
    return _intersection(set(args))


def _union(types: Set[an.TypeAnnot]) -> an.TypeAnnot:
    return contract_types(set.union(*[unit.expand() for unit in types]))


def union(*args: an.TypeAnnot) -> an.TypeAnnot:
    """
    Returns the simplest type containing all the args.
    """
    return _union(set(args))


def contains(inner: an.TypeAnnot, outer: an.TypeAnnot) -> bool:
    """
    Checks if the inner type is contained by the outer type (defers to union).
    """
    return union(outer, inner) == contract_types(outer.expand())


def valid(type_annot: an.TypeAnnot) -> bool:
    """
    Checks if a type annotation is a valid type for a value to have.
    """
    if isinstance(type_annot, an.BuiltinTypeAnnot):
        return True
    if isinstance(type_annot, an.FuncTypeAnnot):
        return all(valid(param) for param in type_annot.params) and (
            valid(type_annot.return_type) or type_annot.return_type == an.VOID
        )
    if isinstance(type_annot, an.OptionalTypeAnnot):
        # Don't allow nested optionals
        return not isinstance(type_annot.target, an.OptionalTypeAnnot) and valid(
            type_annot.target
        )
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
            node.type_annot = node.val_type.type_annot
            if not contains(node.val_init.type_annot, node.type_annot):
                self.errors.add(
                    message=f"mismatched type for value initializer: "
                    f"expected {node.type_annot} but got {node.val_init.type_annot}",
                    regions=[node.val_init.region],
                )
        else:
            node.type_annot = node.val_init.type_annot
            if node.type_annot == an.VOID:
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
            and node.return_type.type_annot != an.VOID
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
            {value for value in an.BuiltinTypeAnnot if value != an.VOID}
        )
        if node.expr and not contains(node.expr.type_annot, printable_types):
            self.errors.add(
                message=f"unprintable type {node.expr.type_annot}",
                regions=[node.region],
            )

    def _check_cond(self, cond: ast.AstExpr) -> None:
        if cond.type_annot != an.BOOL:
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
            if self.expected_returns[-1] != an.VOID:
                self.errors.add(
                    message=f"missing return value in non-void function",
                    regions=[node.region],
                )

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        super().expr_stmt(node)
        if not valid(node.expr.type_annot) and node.expr.type_annot != an.VOID:
            self.errors.add(
                f"invalid expression type {node.expr.type_annot}",
                regions=[node.expr.region],
            )
        if node.expr.type_annot != an.VOID:
            self.errors.add(
                message=f"unused non-void value",
                regions=[node.expr.region],
                severity=er.Severity.WARNING,
            )

    def unary_expr(self, node: ast.AstUnaryExpr) -> None:
        super().unary_expr(node)
        operator = str(node.operator)
        if operator in an.TYPED_UNARY:
            for overload, opcodes in an.TYPED_UNARY[operator].overloads.items():
                if overload.params == [node.target.type_annot]:
                    node.type_annot = overload.return_type
                    node.opcodes = opcodes
                    break
            else:
                self.errors.add(
                    message=f"invalid operand type "
                    f"{node.target.type_annot} "
                    f"for unary operator {node.operator}",
                    regions=[node.region],
                )
        elif operator in an.UNTYPED_UNARY:
            node.type_annot = an.UNTYPED_UNARY[operator].return_type
            node.opcodes = an.UNTYPED_UNARY[operator].opcodes
        else:
            self.errors.add(
                message=f"unknown unary operator {node.operator}",
                regions=[node.operator.lexeme],
            )

    def binary_expr(self, node: ast.AstBinaryExpr) -> None:
        super().binary_expr(node)
        operator = str(node.operator)
        if operator in an.TYPED_BINARY:
            for overload, opcodes in an.TYPED_BINARY[operator].overloads.items():
                if overload.params == [node.left.type_annot, node.right.type_annot]:
                    node.type_annot = overload.return_type
                    node.opcodes = opcodes
                    break
            else:
                self.errors.add(
                    message=f"invalid operand types "
                    f"{node.left.type_annot}, {node.right.type_annot} "
                    f"for binary operator {node.operator}",
                    regions=[node.region],
                )
        elif operator in an.UNTYPED_BINARY:
            node.type_annot = an.UNTYPED_BINARY[operator].return_type
            node.opcodes = an.UNTYPED_BINARY[operator].opcodes
        else:
            self.errors.add(
                message=f"unknown binary operator {node.operator}",
                regions=[node.operator.lexeme],
            )

    def int_expr(self, node: ast.AstIntExpr) -> None:
        super().int_expr(node)
        node.type_annot = an.INT

    def num_expr(self, node: ast.AstNumExpr) -> None:
        super().num_expr(node)
        node.type_annot = an.NUM

    def str_expr(self, node: ast.AstStrExpr) -> None:
        super().str_expr(node)
        node.type_annot = an.STR

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        super().ident_expr(node)
        if node.ref:
            node.type_annot = node.ref.type_annot
        elif node.name in an.BUILTINS:
            node.type_annot = an.BUILTINS[node.name].type_annot

    def bool_expr(self, node: ast.AstBoolExpr) -> None:
        super().bool_expr(node)
        node.type_annot = an.BOOL

    def nil_expr(self, node: ast.AstNilExpr) -> None:
        super().nil_expr(node)
        node.type_annot = an.NIL

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
                    self.errors.add(
                        message=f"mismatched type for argument: "
                        f"expected {param} but got {arg.type_annot}",
                        regions=[arg.region],
                    )
        node.type_annot = node.function.type_annot.return_type

    def ident_type(self, node: ast.AstIdentType) -> None:
        super().ident_type(node)
        if node.ref:
            # TODO: User types
            self.errors.add(message=f"invalid type {node.name}", regions=[node.region])
        else:
            node.type_annot = an.BuiltinTypeAnnot(node.name)

    def void_type(self, node: ast.AstVoidType) -> None:
        super().void_type(node)
        node.type_annot = an.VOID

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
        if not valid(node.type_annot) and node.type_annot != an.VOID:
            self.errors.add(
                message=f"invalid type {node.type_annot}", regions=[node.region]
            )
