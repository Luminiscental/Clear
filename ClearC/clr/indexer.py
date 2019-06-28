"""
Module defining a visitor to index identifiers of an ast.
"""

from typing import List

import copy

import clr.ast as ast
import clr.annotations as an


class UpvalueTracker(ast.FunctionVisitor):
    """
    Ast visitor to annotate the upvalues of functions.
    """

    def __init__(self) -> None:
        super().__init__()
        self.neutral_bindings: List[ast.AstIdentRef] = []

    def start(self, node: ast.Ast) -> None:
        for decl in node.decls:
            if isinstance(decl, ast.AstValueDecl):
                self.neutral_bindings.extend(decl.bindings)
            if isinstance(decl, ast.AstFuncDecl):
                self.neutral_bindings.append(decl)
        super().start(node)

    def case_expr(self, node: ast.AstCaseExpr) -> None:
        self.neutral_bindings.append(node.binding)
        super().case_expr(node)

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        super().ident_expr(node)
        if node.ref:
            if (
                # In a function
                self._functions
                # Not a case/global binding
                and node.ref not in self.neutral_bindings
                # Not a param to the function
                and node.ref not in self._functions[-1].params
                # Not already an upvalue
                and node.ref not in self._functions[-1].upvalues
                # Not local to the function
                and node.ref not in self._get_scope().names.values()
            ):
                # Add as an upvalue
                self._functions[-1].upvalues.append(node.ref)


class Indexer(ast.FunctionVisitor):
    """
    Ast visitor to annotate the indices and index types of identifiers.
    """

    def __init__(self) -> None:
        super().__init__()
        self._global_count = 0
        self._temporary_count = 0
        self._local_counts: List[int] = []
        self._param_counts: List[int] = []

    def _declare(self) -> an.IndexAnnot:
        if len(self._scopes) == 1:
            result = an.IndexAnnot(
                value=self._global_count, kind=an.IndexAnnotType.GLOBAL
            )
            self._global_count += 1
        else:
            result = an.IndexAnnot(
                value=self._local_counts[-1], kind=an.IndexAnnotType.LOCAL
            )
            self._local_counts[-1] += 1
        return result

    def _load(self, ref: ast.AstIdentRef) -> an.IndexAnnot:
        if self._functions:
            function = self._functions[-1]
            if ref == function:
                # It's the recursion upvalue
                return an.IndexAnnot(value=0, kind=an.IndexAnnotType.UPVALUE)
            if ref in function.upvalues:
                # It's a normal upvalue
                return an.IndexAnnot(
                    value=1 + function.upvalues.index(ref),
                    kind=an.IndexAnnotType.UPVALUE,
                )
        # Not an upvalue so load from the declaration
        result = copy.copy(ref.index_annot)  # Copy because we may mutate the value
        if result.kind == an.IndexAnnotType.LOCAL and self._functions:
            result.value += 1 + len(self._functions[-1].params)
        return result

    def start(self, node: ast.Ast) -> None:
        self._local_counts.append(0)  # This stays 0 because it's the global scope
        super().start(node)
        self._local_counts.pop()

    def value_decl(self, node: ast.AstValueDecl) -> None:
        super().value_decl(node)
        self._temporary_count = 0

    def binding(self, node: ast.AstBinding) -> None:
        super().binding(node)
        node.index_annot = self._declare()

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        node.index_annot = self._declare()
        for upvalue in node.upvalues:
            node.upvalue_refs.append(self._load(upvalue))
        self._param_counts.append(0)
        # Reset the locals
        self._local_counts.append(0)
        super().func_decl(node)
        self._local_counts.pop()
        self._param_counts.pop()

    def param(self, node: ast.AstParam) -> None:
        super().param(node)
        node.index_annot = an.IndexAnnot(
            value=1 + self._param_counts[-1], kind=an.IndexAnnotType.PARAM
        )
        self._param_counts[-1] += 1

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        super().print_stmt(node)
        self._temporary_count = 0

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        self._local_counts.append(self._local_counts[-1])
        super().block_stmt(node)
        self._local_counts.pop()

    def if_stmt(self, node: ast.AstIfStmt) -> None:
        node.if_part[0].accept(self)
        self._temporary_count = 0
        for elif_cond, elif_block in node.elif_parts:
            elif_cond.accept(self)
            self._temporary_count = 0
            elif_block.accept(self)
        if node.else_part:
            node.else_part.accept(self)

    def while_stmt(self, node: ast.AstWhileStmt) -> None:
        if node.cond:
            node.cond.accept(self)
            self._temporary_count = 0
        node.block.accept(self)

    def return_stmt(self, node: ast.AstReturnStmt) -> None:
        super().return_stmt(node)
        self._temporary_count = 0

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        super().expr_stmt(node)
        self._temporary_count = 0

    def binary_expr(self, node: ast.AstBinaryExpr) -> None:
        super().binary_expr(node)
        self._temporary_count -= 1

    def int_expr(self, node: ast.AstIntExpr) -> None:
        super().int_expr(node)
        self._temporary_count += 1

    def num_expr(self, node: ast.AstNumExpr) -> None:
        super().num_expr(node)
        self._temporary_count += 1

    def str_expr(self, node: ast.AstStrExpr) -> None:
        super().str_expr(node)
        self._temporary_count += 1

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        super().ident_expr(node)
        # If the ref is None there was already an error
        if node.ref:
            node.index_annot = self._load(node.ref)
        self._temporary_count += 1

    def bool_expr(self, node: ast.AstBoolExpr) -> None:
        super().bool_expr(node)
        self._temporary_count += 1

    def nil_expr(self, node: ast.AstNilExpr) -> None:
        super().nil_expr(node)
        self._temporary_count += 1

    def case_expr(self, node: ast.AstCaseExpr) -> None:
        node.target.accept(self)
        node.binding.index_annot = an.IndexAnnot(
            value=self._temporary_count + self._local_counts[-1] - 1,
            kind=an.IndexAnnotType.LOCAL,
        )
        for _, value in node.cases:
            value.accept(self)
            self._temporary_count -= 1
        if node.fallback:
            node.fallback.accept(self)
            self._temporary_count -= 1

    def call_expr(self, node: ast.AstCallExpr) -> None:
        super().call_expr(node)
        self._temporary_count -= len(node.args)

    def tuple_expr(self, node: ast.AstTupleExpr) -> None:
        super().tuple_expr(node)
        self._temporary_count -= len(node.exprs) - 1
