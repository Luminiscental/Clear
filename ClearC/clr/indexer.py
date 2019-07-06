"""
Module defining a visitor to index identifiers of an ast.
"""

from typing import List, Iterator

import contextlib as cx

import clr.ast as ast
import clr.annotations as an


class UpvalueTracker(ast.ContextVisitor):
    """
    Ast visitor to annotate the upvalues of functions.
    """

    def __init__(self) -> None:
        super().__init__()
        self._global_refs: List[ast.AstBinding] = []

    def start(self, node: ast.Ast) -> None:
        for decl in node.decls:
            if isinstance(decl, ast.AstValueDecl):
                for binding in decl.bindings:
                    self._global_refs.append(binding)
            elif isinstance(decl, ast.AstFuncDecl):
                self._global_refs.append(decl.binding)
            decl.accept(self)

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        if node.ref:
            # Globals can always be referenced directly
            if node.ref in self._global_refs:
                return
            # Find all the functions between the declaration and the reference
            functions = []
            for context in reversed(self._contexts):
                if (
                    isinstance(context, ast.AstScope)
                    and node.ref in context.names.values()
                ):
                    break
                if (
                    isinstance(context, ast.AstFuncDecl)
                    and node.ref in context.block.names.values()
                ):
                    break
                if isinstance(context, ast.AstFunction):
                    functions.append(context)
            # Add it as an upvalue to any such functions
            for function in functions:
                if node.ref not in function.upvalues:
                    function.upvalues.append(node.ref)


class IndexBuilder(ast.ContextVisitor):
    """
    Ast visitor to create indices for declarations.
    """

    def __init__(self) -> None:
        super().__init__()
        self._name_counts: List[int] = []
        self._frames: List[int] = []

    def _push_context(self, context: ast.AstContext) -> None:
        super()._push_context(context)
        if isinstance(context, ast.AstFunction):
            # Reset to just the function struct on the stack
            self._name_counts.append(1)
            self._frames.append(1)
        elif isinstance(context, ast.AstScope):
            base_names = 0
            base_stack = 0
            # If we're already in a non-global scope
            if len(self._name_counts) > 1:
                # Names from previous scopes remain underneath
                base_names = self._name_counts[-1]
                base_stack = self._frames[-1]
            self._name_counts.append(base_names)
            self._frames.append(base_stack)

    def _pop_context(self) -> ast.AstContext:
        context = super()._pop_context()
        if isinstance(context, (ast.AstFunction, ast.AstScope)):
            self._name_counts.pop()
            self._frames.pop()
        return context

    def _make_index(self) -> an.IndexAnnot:
        # Get the index value based on how many indices are already in scope
        value = self._name_counts[-1]
        self._name_counts[-1] += 1
        # Get the kind based on how many index scopes there are
        if len(self._name_counts) == 1:
            kind = an.IndexAnnotType.GLOBAL
        else:
            kind = an.IndexAnnotType.LOCAL
            self._frames[-1] += 1
        return an.IndexAnnot(value, kind)

    def _temp_index(self) -> an.IndexAnnot:
        return an.IndexAnnot(value=self._frames[-1] - 1, kind=an.IndexAnnotType.LOCAL)

    @cx.contextmanager
    def _stack(self, offset: int) -> Iterator[None]:
        prev_stack = self._frames[-1]
        yield
        self._frames[-1] = prev_stack + offset

    def binding(self, node: ast.AstBinding) -> None:
        node.index_annot = self._make_index()

    def param(self, node: ast.AstParam) -> None:
        if not isinstance(self._get_context(), ast.AstStructDecl):
            super().param(node)
            node.binding.index_annot.kind = an.IndexAnnotType.PARAM

    def value_decl(self, node: ast.AstValueDecl) -> None:
        node.val_init.accept(self)
        self._frames[-1] -= 1
        for binding in node.bindings:
            binding.accept(self)

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        with self._stack(0):
            super().print_stmt(node)

    def if_stmt(self, node: ast.AstIfStmt) -> None:
        conds = [node.if_part] + node.elif_parts
        for condition, block in conds:
            with self._stack(0):
                condition.accept(self)
            block.accept(self)
        if node.else_part:
            node.else_part.accept(self)

    def while_stmt(self, node: ast.AstWhileStmt) -> None:
        if node.cond:
            with self._stack(0):
                node.cond.accept(self)
        node.block.accept(self)

    def return_stmt(self, node: ast.AstReturnStmt) -> None:
        with self._stack(0):
            super().return_stmt(node)

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        with self._stack(0):
            super().expr_stmt(node)

    def binary_expr(self, node: ast.AstBinaryExpr) -> None:
        with self._stack(+1):
            super().binary_expr(node)

    def int_expr(self, node: ast.AstIntExpr) -> None:
        self._frames[-1] += 1

    def num_expr(self, node: ast.AstNumExpr) -> None:
        self._frames[-1] += 1

    def str_expr(self, node: ast.AstStrExpr) -> None:
        self._frames[-1] += 1

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        self._frames[-1] += 1

    def bool_expr(self, node: ast.AstBoolExpr) -> None:
        self._frames[-1] += 1

    def nil_expr(self, node: ast.AstNilExpr) -> None:
        self._frames[-1] += 1

    def case_expr(self, node: ast.AstCaseExpr) -> None:
        with self._stack(+1):
            node.target.accept(self)
            node.binding.index_annot = self._temp_index()
            for case_type, case_expr in node.cases:
                case_type.accept(self)
                case_expr.accept(self)
            if node.fallback:
                node.fallback.accept(self)

    def call_expr(self, node: ast.AstCallExpr) -> None:
        with self._stack(+1):
            super().call_expr(node)

    def tuple_expr(self, node: ast.AstTupleExpr) -> None:
        with self._stack(+1):
            super().tuple_expr(node)

    def lambda_expr(self, node: ast.AstLambdaExpr) -> None:
        with self._stack(+1):
            super().lambda_expr(node)

    def construct_expr(self, node: ast.AstConstructExpr) -> None:
        with self._stack(+1):
            super().construct_expr(node)
        node.index_annot = self._temp_index()


class IndexWriter(ast.ContextVisitor):
    """
    Ast visitor to annotate the indices of name references.
    """

    def _load(self, ref: ast.AstBinding) -> an.IndexAnnot:
        for context in reversed(self._contexts):
            if isinstance(context, ast.AstFunction):
                function = context
                break
        else:
            return ref.index_annot
        if ref == function:
            # It's the recursion upvalue
            return an.IndexAnnot(value=0, kind=an.IndexAnnotType.UPVALUE)
        if ref in function.upvalues:
            # It's a normal upvalue
            return an.IndexAnnot(
                value=1 + function.upvalues.index(ref), kind=an.IndexAnnotType.UPVALUE
            )
        return ref.index_annot

    def _pop_context(self) -> ast.AstContext:
        context = super()._pop_context()
        if isinstance(context, ast.AstFunction):
            context.upvalue_indices = [
                self._load(upvalue) for upvalue in context.upvalues
            ]
        return context

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        if node.ref:
            node.index_annot = self._load(node.ref)
