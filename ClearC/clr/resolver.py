"""
Module for name resolution visitors / functions.
"""

from typing import Union, Optional, List, DefaultDict

import collections as co

import clr.ast as ast
import clr.types as ts
import clr.errors as er

# TODO: Warn on unused declarations


class DuplicateChecker(ast.DeepVisitor):
    """
    Ast visitor to check for duplicate names in struct and constructors.
    """

    def _duplicate(
        self, region: er.SourceView, prev: List[er.SourceView], kind: str
    ) -> None:
        self.errors.add(message=f"duplicate {kind} {region}", regions=[region] + prev)

    def struct_decl(self, node: ast.AstStructDecl) -> None:
        super().struct_decl(node)
        names: DefaultDict[str, List[er.SourceView]] = co.defaultdict(list)
        for param in node.params:
            if param.binding.name in names:
                self._duplicate(
                    param.binding.region, names[param.binding.name], "struct parameter"
                )
            names[param.binding.name].append(param.binding.region)
        for _, bindings in node.generators:
            for binding in bindings:
                if binding.name in names:
                    self._duplicate(
                        binding.region, names[binding.name], "struct declaration"
                    )
                names[binding.name].append(binding.region)

    def construct_expr(self, node: ast.AstConstructExpr) -> None:
        super().construct_expr(node)
        names: DefaultDict[str, List[er.SourceView]] = co.defaultdict(list)
        for label, _ in node.inits:
            if label.name in names:
                self._duplicate(label.region, names[label.name], "field specifier")
            names[label.name].append(label.region)


class NameTracker(ast.ContextVisitor):
    """
    Ast visitor to annotate what names are in scope.
    """

    def _set_name(self, name: str, node: ast.AstName) -> None:
        for context in reversed(self._contexts):
            if isinstance(context, ast.AstScope):
                names = context.names
                break
            if isinstance(context, ast.AstFuncDecl):
                names = context.block.names
                break
        if name in names:
            self.errors.add(
                message=f"redefinition of name {name}",
                regions=[node.region, names[name].region],
            )
        names[name] = node

    def _decl(self, node: ast.AstDecl) -> None:
        node.context = self._get_context()

    def struct_decl(self, node: ast.AstStructDecl) -> None:
        super().struct_decl(node)
        self._set_name(node.name, node)

    def binding(self, node: ast.AstBinding) -> None:
        if not isinstance(self._get_context(), ast.AstStructDecl):
            self._set_name(node.name, node)


class NameResolver(ast.ContextVisitor):
    """
    Ast visitor to annotate what declarations identifiers reference.
    """

    def _get_name(self, name: str) -> Optional[ast.AstName]:
        for context in reversed(self._contexts):
            if isinstance(context, ast.AstScope):
                if name in context.names:
                    return context.names[name]
            if isinstance(context, ast.AstFuncDecl):
                if name in context.block.names:
                    return context.block.names[name]
        return None

    def _resolve_name(
        self,
        name: str,
        node: Union[ast.AstIdentExpr, ast.AstIdentType, ast.AstConstructExpr],
    ) -> None:
        ref = self._get_name(name)
        if ref is None:
            self.errors.add(
                message=f"reference to undeclared name {name}", regions=[node.region]
            )
            return
        if isinstance(node, (ast.AstConstructExpr, ast.AstIdentType)):
            if isinstance(ref, ast.AstStructDecl):
                node.ref = ref
            else:
                self.errors.add(
                    message=f"invalid reference to value {node.name}, expected struct",
                    regions=[node.region],
                )
        else:
            if isinstance(ref, ast.AstStructDecl):
                self.errors.add(
                    message=f"invalid reference to struct {node.name}, expected value",
                    regions=[node.region],
                )
            else:
                node.ref = ref

    def value_decl(self, node: ast.AstValueDecl) -> None:
        super().value_decl(node)
        for binding in node.bindings:
            binding.dependency = node

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        super().func_decl(node)
        node.binding.dependency = node

    def set_stmt(self, node: ast.AstSetStmt) -> None:
        super().set_stmt(node)
        for context in reversed(self._contexts):
            if (
                isinstance(context, ast.AstFuncDecl)
                and node.target.ref == context.binding
            ):
                self.errors.add(
                    message=f"cannot set function within its own body",
                    regions=[context.binding.region, node.target.region],
                )

    def construct_expr(self, node: ast.AstConstructExpr) -> None:
        self._resolve_name(node.name, node)
        super().construct_expr(node)
        for context in reversed(self._contexts):
            if context == node.ref:
                node.inside = True

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        if node.name not in ts.BUILTINS:
            self._resolve_name(node.name, node)
            if node.name == "this":
                node.struct = self._get_struct()

    def ident_type(self, node: ast.AstIdentType) -> None:
        if node.name not in {annot.value for annot in ts.BuiltinType}:
            self._resolve_name(node.name, node)
