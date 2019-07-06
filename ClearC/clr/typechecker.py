"""
Module defining an ast visitor to type check.
"""

from typing import List, Dict, Union

import clr.errors as er
import clr.ast as ast
import clr.types as ts


class TypeChecker(ast.DeepVisitor):
    """
    Ast visitor to annotate and check types.
    """

    def __init__(self) -> None:
        super().__init__()
        self.expected_returns: List[ts.Type] = []

    def struct_decl(self, node: ast.AstStructDecl) -> None:
        node.type_annot = ts.StructType.make(node)
        for param in node.params:
            param.accept(self)
        for generator, _ in node.generators:
            self.expected_returns.append(ts.ANY)
            generator.block.accept(self)
            self.expected_returns.pop()

    def value_decl(self, node: ast.AstValueDecl) -> None:
        super().value_decl(node)
        # Handle overall type
        if node.val_type:
            node.type_annot = node.val_type.type_annot
            if not ts.contains(node.val_init.type_annot, node.type_annot):
                self.errors.add(
                    message=f"mismatched type for value initializer: "
                    f"expected {node.type_annot} but got {node.val_init.type_annot}",
                    regions=[node.val_init.region],
                )
        else:
            node.type_annot = node.val_init.type_annot
            if node.type_annot == ts.VOID:
                self.errors.add(
                    message="cannot declare value as void",
                    regions=[node.val_init.region],
                )
        # Distribute to bindings
        if len(node.bindings) == 1:
            node.bindings[0].type_annot = node.type_annot
        else:
            as_tuple = node.type_annot.get_tuple()
            if as_tuple is None:
                self.errors.add(
                    message=f"cannot unpack non-tuple type {node.type_annot}",
                    regions=[node.region],
                )
            else:
                if len(as_tuple.elements) != len(node.bindings):
                    adjective = (
                        "few" if len(as_tuple.elements) < len(node.bindings) else "many"
                    )
                    self.errors.add(
                        message=f"too {adjective} bindings to unpack tuple of size {len(as_tuple.elements)}",
                        regions=[node.region],
                    )
                for subtype, binding in zip(as_tuple.elements, node.bindings):
                    binding.type_annot = subtype

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        for param in node.params:
            param.accept(self)
        node.return_type.accept(self)
        if (
            not ts.valid(node.return_type.type_annot)
            and node.return_type.type_annot != ts.VOID
        ):
            self.errors.add(
                message=f"invalid return type {node.return_type.type_annot}",
                regions=[node.return_type.region],
            )
        node.binding.type_annot = ts.FunctionType.make(
            [param.binding.type_annot for param in node.params],
            node.return_type.type_annot,
        )
        self.expected_returns.append(node.return_type.type_annot)
        node.block.accept(self)
        self.expected_returns.pop()
        node.type_annot = node.binding.type_annot

    def param(self, node: ast.AstParam) -> None:
        super().param(node)
        node.binding.type_annot = node.param_type.type_annot
        if not ts.valid(node.binding.type_annot):
            self.errors.add(
                message=f"invalid type {node.binding.type_annot} for parameter",
                regions=[node.region],
            )

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        super().print_stmt(node)
        str_func = ts.BUILTINS["str"].type_annot.get_function()
        if str_func is not None:  # Should be true
            printable = ts.union((str_func.parameters[0], ts.STR))
            if node.expr and not ts.contains(node.expr.type_annot, printable):
                self.errors.add(
                    message=f"unprintable type {node.expr.type_annot}",
                    regions=[node.region],
                )

    def _check_cond(self, cond: ast.AstExpr) -> None:
        if cond.type_annot != ts.BOOL:
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
            if not ts.valid(node.expr.type_annot):
                self.errors.add(
                    message=f"invalid type {node.expr.type_annot} to return",
                    regions=[node.expr.region],
                )
            elif not ts.contains(node.expr.type_annot, self.expected_returns[-1]):
                self.errors.add(
                    message=f"mismatched return type: "
                    f"expected {self.expected_returns[-1]} but got {node.expr.type_annot}",
                    regions=[node.expr.region],
                )
        else:
            if self.expected_returns[-1] != ts.VOID:
                self.errors.add(
                    message=f"missing return value in non-void function",
                    regions=[node.region],
                )

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        super().expr_stmt(node)
        if not ts.valid(node.expr.type_annot) and node.expr.type_annot != ts.VOID:
            self.errors.add(
                f"invalid expression type {node.expr.type_annot}",
                regions=[node.expr.region],
            )
        if node.expr.type_annot != ts.VOID:
            self.errors.add(
                message=f"unused non-void value",
                regions=[node.expr.region],
                severity=er.Severity.WARNING,
            )

    def _operator(
        self,
        args: List[ts.Type],
        operator: str,
        node: Union[ast.AstUnaryExpr, ast.AstBinaryExpr],
    ) -> None:
        if operator in ts.TYPED_OPERATORS:
            for overload, opcodes in ts.TYPED_OPERATORS[operator].overloads.items():
                if overload.parameters == args:
                    node.type_annot = overload.return_type
                    node.opcodes = opcodes
                    break
            else:
                types = ", ".join(str(arg) for arg in args)
                self.errors.add(
                    message=f"invalid operand types {types} for operator {operator}",
                    regions=[node.region],
                )
        elif operator in ts.UNTYPED_OPERATORS:
            node.type_annot = ts.UNTYPED_OPERATORS[operator].return_type
            node.opcodes = ts.UNTYPED_OPERATORS[operator].opcodes
        else:
            self.errors.add(
                message=f"unknown operator {operator}", regions=[node.operator.lexeme]
            )

    def unary_expr(self, node: ast.AstUnaryExpr) -> None:
        super().unary_expr(node)
        self._operator([node.target.type_annot], str(node.operator), node)

    def binary_expr(self, node: ast.AstBinaryExpr) -> None:
        super().binary_expr(node)
        self._operator(
            [node.left.type_annot, node.right.type_annot], str(node.operator), node
        )

    def int_expr(self, node: ast.AstIntExpr) -> None:
        node.type_annot = ts.INT

    def num_expr(self, node: ast.AstNumExpr) -> None:
        node.type_annot = ts.NUM

    def str_expr(self, node: ast.AstStrExpr) -> None:
        node.type_annot = ts.STR

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        if node.ref:
            node.type_annot = node.ref.type_annot
        else:
            node.type_annot = ts.BUILTINS[node.name].type_annot

    def bool_expr(self, node: ast.AstBoolExpr) -> None:
        node.type_annot = ts.BOOL

    def nil_expr(self, node: ast.AstNilExpr) -> None:
        node.type_annot = ts.NIL

    def case_expr(self, node: ast.AstCaseExpr) -> None:
        node.target.accept(self)
        cases: Dict[ts.Type, ast.AstType] = {}
        output_type = ts.Type(set())
        for case_type, case_value in node.cases:
            # Check if the case type is valid
            case_type.accept(self)
            if not ts.contains(case_type.type_annot, node.target.type_annot):
                self.errors.add(
                    message=f"invalid case {case_type.type_annot} for type {node.target.type_annot}",
                    regions=[case_type.region, node.target.region],
                )
            if case_type.type_annot in cases:
                self.errors.add(
                    message=f"duplicate case {case_type.type_annot}",
                    regions=[case_type.region, cases[case_type.type_annot].region],
                )
            cases[case_type.type_annot] = case_type
            # Get the case value type
            node.binding.type_annot = case_type.type_annot
            case_value.accept(self)
            output_type = ts.union((output_type, case_value.type_annot))
        matched_types = ts.union(cases.keys())
        complete = ts.contains(node.target.type_annot, matched_types)
        remaining = ts.difference(node.target.type_annot, matched_types)
        if node.fallback:
            if complete:
                self.errors.add(
                    message=f"redundant fallback",
                    regions=[node.fallback.region],
                    severity=er.Severity.WARNING,
                )
            node.binding.type_annot = remaining
            node.fallback.accept(self)
            output_type = ts.union((output_type, node.fallback.type_annot))
        elif not complete:
            self.errors.add(
                message=f"incomplete case expression, missing case(s) for {remaining}",
                regions=[node.region],
            )
        node.type_annot = output_type

    def call_expr(self, node: ast.AstCallExpr) -> None:
        super().call_expr(node)
        as_func = node.function.type_annot.get_function()
        if as_func is None:
            self.errors.add(
                message=f"invalid type {node.function.type_annot} to call, expected a function",
                regions=[node.function.region],
            )
            return
        arg_count = len(node.args)
        param_count = len(as_func.parameters)
        if arg_count != param_count:
            adjective = "few" if arg_count < param_count else "many"
            self.errors.add(
                message=f"too {adjective} arguments to function: "
                f"expected {param_count} but got {arg_count}",
                regions=[
                    er.SourceView.range(node.args[0].region, node.args[-1].region)
                ],
            )
        for arg, param in zip(node.args, as_func.parameters):
            if not ts.contains(arg.type_annot, param):
                self.errors.add(
                    message=f"mismatched type for argument: "
                    f"expected {param} but got {arg.type_annot}",
                    regions=[arg.region],
                )
        node.type_annot = as_func.return_type

    def tuple_expr(self, node: ast.AstTupleExpr) -> None:
        super().tuple_expr(node)
        node.type_annot = ts.TupleType.make([elem.type_annot for elem in node.exprs])

    def lambda_expr(self, node: ast.AstLambdaExpr) -> None:
        super().lambda_expr(node)
        node.type_annot = ts.FunctionType.make(
            [param.binding.type_annot for param in node.params], node.value.type_annot
        )

    def construct_expr(self, node: ast.AstConstructExpr) -> None:
        super().construct_expr(node)
        if node.ref is None:
            return
        struct_type = node.ref.type_annot.get_struct()
        if struct_type is None:
            self.errors.add(
                message=f"cannot construct non-struct type {node.ref.type_annot}",
                regions=[node.region],
            )
            return
        for param in struct_type.ref.params:
            if param.binding.name not in node.inits:
                self.errors.add(
                    message=f"missing field {param.binding.name} in constructor",
                    regions=[param.region, node.region],
                )
            else:
                init_expr = node.inits[param.binding.name]
                if init_expr.type_annot != param.param_type.type_annot:
                    self.errors.add(
                        message=f"mismatched type for field, expected {param.param_type.type_annot} but got {init_expr.type_annot}",
                        regions=[param.param_type.region, init_expr.region],
                    )
        node.type_annot = node.ref.type_annot

    def access_expr(self, node: ast.AstAccessExpr) -> None:
        super().access_expr(node)
        struct_type = node.target.type_annot.get_struct()
        if struct_type is None:
            self.errors.add(
                message=f"cannot access field from non-struct type {node.target.type_annot}",
                regions=[node.region],
            )
        else:
            node.ref = struct_type.ref
            for binding in struct_type.ref.iter_bindings():
                if node.name == binding.name:
                    node.type_annot = binding.type_annot
                    break
            else:
                self.errors.add(
                    message=f"reference to undeclared field {node.name} for struct {struct_type}",
                    regions=[node.region],
                )

    def ident_type(self, node: ast.AstIdentType) -> None:
        if node.ref:
            node.type_annot = ts.StructType.make(node.ref)
        else:
            node.type_annot = ts.BuiltinType.get(node.name)

    def void_type(self, node: ast.AstVoidType) -> None:
        node.type_annot = ts.VOID

    def func_type(self, node: ast.AstFuncType) -> None:
        super().func_type(node)
        node.type_annot = ts.FunctionType.make(
            [param.type_annot for param in node.params], node.return_type.type_annot
        )
        if not ts.valid(node.type_annot):
            self.errors.add(
                message=f"invalid type {node.type_annot}", regions=[node.region]
            )

    def optional_type(self, node: ast.AstOptionalType) -> None:
        super().optional_type(node)
        node.type_annot = ts.union((node.target.type_annot, ts.NIL))
        if not ts.valid(node.type_annot):
            self.errors.add(
                message=f"invalid type {node.type_annot}", regions=[node.region]
            )

    def union_type(self, node: ast.AstUnionType) -> None:
        super().union_type(node)
        node.type_annot = ts.union(elem.type_annot for elem in node.types)
        if not ts.valid(node.type_annot) and node.type_annot != ts.VOID:
            self.errors.add(
                message=f"invalid type {node.type_annot}", regions=[node.region]
            )

    def tuple_type(self, node: ast.AstTupleType) -> None:
        super().tuple_type(node)
        node.type_annot = ts.TupleType.make([elem.type_annot for elem in node.types])
        if not ts.valid(node.type_annot):
            self.errors.add(
                message=f"invalid type {node.type_annot}", regions=[node.region]
            )
