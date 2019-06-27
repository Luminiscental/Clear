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

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        super().ident_expr(node)
        if node.ref:
            if (
                # In a function
                self._functions
                # Not local to the function
                and node.ref not in self._get_scope().names.values()
                # Not global
                and node.ref not in self._scopes[0].decls
                # Not a param to the function
                and node.ref not in self._functions[-1].params
                # Not already an upvalue
                and node.ref not in self._functions[-1].upvalues
            ):
                # Add as an upvalue
                self._functions[-1].upvalues.append(node.ref)


class Indexer(ast.FunctionVisitor):
    """
    Ast visitor to annotate the indices and index types of identifiers.
    """

    def __init__(self) -> None:
        super().__init__()
        self._global_index = 0
        self._local_indices: List[int] = []
        self._param_indices: List[int] = []

    def _declare(self) -> an.IndexAnnot:
        if len(self._scopes) == 1:
            result = an.IndexAnnot(
                value=self._global_index, kind=an.IndexAnnotType.GLOBAL
            )
            self._global_index += 1
        else:
            result = an.IndexAnnot(
                value=self._local_indices[-1], kind=an.IndexAnnotType.LOCAL
            )
            self._local_indices[-1] += 1
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

    def binding(self, node: ast.AstBinding) -> None:
        node.index_annot = self._declare()

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        node.index_annot = self._declare()
        for upvalue in node.upvalues:
            node.upvalue_refs.append(self._load(upvalue))
        self._param_indices.append(0)
        # Reset the locals
        self._local_indices.append(0)
        super().func_decl(node)
        self._local_indices.pop()
        self._param_indices.pop()

    def param(self, node: ast.AstParam) -> None:
        node.index_annot = an.IndexAnnot(
            value=1 + self._param_indices[-1], kind=an.IndexAnnotType.PARAM
        )
        self._param_indices[-1] += 1

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        self._local_indices.append(
            self._local_indices[-1] if self._local_indices else 0
        )
        super().block_stmt(node)
        self._local_indices.pop()

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        super().ident_expr(node)
        # If the ref is None there was already an error
        if node.ref:
            node.index_annot = self._load(node.ref)
