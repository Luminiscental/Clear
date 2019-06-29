"""
Module defining a visitor to index identifiers of an ast.
"""

from typing import List

import clr.ast as ast
import clr.annotations as an
import clr.util as util


class UpvalueTracker(ast.FunctionVisitor):
    """
    Ast visitor to annotate the upvalues of functions.
    """

    def __init__(self) -> None:
        super().__init__()
        self._global_refs: List[ast.AstIdentRef] = []

    def start(self, node: ast.Ast) -> None:
        for decl in node.decls:
            if isinstance(decl, ast.AstValueDecl):
                for binding in decl.bindings:
                    self._global_refs.append(binding)
            elif isinstance(decl, ast.AstFuncDecl):
                self._global_refs.append(decl)
            decl.accept(self)

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        if node.ref:
            # Globals can always be referenced directly
            if node.ref in self._global_refs:
                return
            # No upvalues outside of functions
            if not self._functions:
                return
            function = self._get_function()
            # Params aren't upvalues
            if node.ref in function.params:
                return
            # Don't double count
            if node.ref in function.upvalues:
                return
            # If the function isn't a lambda it can have locals
            if isinstance(function, ast.AstFuncDecl):
                # If it's local to the function it's not an upvalue
                function_scopes = util.break_after(
                    function.block, reversed(self._scopes)
                )
                for scope in function_scopes:
                    if node.ref in scope.names.values():
                        return
            function.upvalues.append(node.ref)


class IndexBuilder(ast.FunctionVisitor):
    """
    Ast visitor to create indices for declarations.
    """

    def __init__(self) -> None:
        super().__init__()
        self._name_counts: List[int] = []

    def _push_scope(self, node: ast.AstScope) -> None:
        super()._push_scope(node)
        base_count = 0
        # If we're already in a non-global scope
        if len(self._name_counts) > 1:
            # Names from previous scopes remain underneath
            base_count = self._name_counts[-1]
        self._name_counts.append(base_count)

    def _push_function(self, function: ast.AstFunction) -> None:
        super()._push_function(function)
        # Functions reset the local scope
        self._name_counts.append(0)

    def _pop_scope(self) -> None:
        super()._pop_scope()
        self._name_counts.pop()

    def _pop_function(self) -> None:
        super()._pop_function()
        self._name_counts.pop()

    def _make_index(self) -> an.IndexAnnot:
        # Get the index value based on how many indices are already in scope
        value = self._name_counts[-1]
        self._name_counts[-1] += 1
        # Get the kind based on how many index scopes there are
        kind = (
            an.IndexAnnotType.GLOBAL
            if len(self._name_counts) == 1
            else an.IndexAnnotType.LOCAL
        )
        # In functions locals are offset by the function struct at the bottom of the call stack
        if self._functions and kind == an.IndexAnnotType.LOCAL:
            value += 1
        return an.IndexAnnot(value, kind)

    def binding(self, node: ast.AstBinding) -> None:
        node.index_annot = self._make_index()

    def param(self, node: ast.AstParam) -> None:
        node.index_annot = self._make_index()
        node.index_annot.kind = an.IndexAnnotType.PARAM

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        super().func_decl(node)
        node.index_annot = self._make_index()


class IndexWriter(ast.FunctionVisitor):
    """
    Ast visitor to annotate the indices of name references.
    """

    def _load(self, ref: ast.AstIdentRef) -> an.IndexAnnot:
        if self._functions:
            function = self._get_function()
            if ref == function:
                # It's the recursion upvalue
                return an.IndexAnnot(value=0, kind=an.IndexAnnotType.UPVALUE)
            if ref in function.upvalues:
                # It's a normal upvalue
                return an.IndexAnnot(
                    value=1 + function.upvalues.index(ref),
                    kind=an.IndexAnnotType.UPVALUE,
                )
        return ref.index_annot

    def _pop_function(self) -> None:
        function = self._get_function()
        super()._pop_function()
        function.upvalue_indices = [
            self._load(upvalue) for upvalue in function.upvalues
        ]

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        if node.ref:
            node.index_annot = self._load(node.ref)
