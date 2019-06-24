"""
Module defining a visitor to index identifiers of an ast.
"""

from typing import List

import clr.ast as ast
import clr.annotations as an


class Indexer(ast.ScopeVisitor):
    """
    Ast visitor to annotate the indices and index types of identifiers.
    """

    def __init__(self) -> None:
        super().__init__()
        self._functions: List[ast.AstFuncDecl] = []
        self._global_index = 0
        self._local_index = 0
        self._param_index = 0

    def _declare(self) -> an.IndexAnnot:
        if len(self._scopes) == 1:
            result = an.IndexAnnot(
                value=self._global_index, kind=an.IndexAnnotType.GLOBAL
            )
            self._global_index += 1
        else:
            result = an.IndexAnnot(
                value=self._local_index, kind=an.IndexAnnotType.LOCAL
            )
            self._local_index += 1
        return result

    def value_decl(self, node: ast.AstValueDecl) -> None:
        node.index_annot = self._declare()
        super().value_decl(node)

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        node.index_annot = self._declare()
        self._functions.append(node)
        super().func_decl(node)
        self._functions.pop()
        # Reset param index
        self._param_index = 0

    def param(self, node: ast.AstParam) -> None:
        node.index_annot = an.IndexAnnot(
            value=self._param_index, kind=an.IndexAnnotType.PARAM
        )
        self._param_index += 1

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        super().block_stmt(node)
        # Reset local index
        self._local_index -= len(node.names)

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        super().ident_expr(node)
        if node.ref:
            if (
                self._functions  # In a function
                and node.ref not in self._get_scope().decls  # Not local to the function
                and node.ref not in self._scopes[0].decls  # Not a global
                and node.ref
                not in self._functions[-1].params  # Not a param to the function
            ):
                # It's an upvalue
                function = self._functions[-1]
                if node.ref in function.upvalues:
                    # If it's already tracked as an upvalue use that index
                    node.index_annot = an.IndexAnnot(
                        value=function.upvalues.index(node.ref),
                        kind=an.IndexAnnotType.UPVALUE,
                    )
                else:
                    # Otherwise add it to the function's upvalues
                    upvalue_index = len(function.upvalues)
                    function.upvalues.append(node.ref)
                    node.index_annot = an.IndexAnnot(
                        value=upvalue_index, kind=an.IndexAnnotType.UPVALUE
                    )
            else:
                # Not an upvalue so just use the declaration
                node.index_annot = node.ref.index_annot
        else:
            self.errors.add(
                message=f"couldn't resolve identifier {node.name}",
                regions=[node.region],
            )
        print(f"{node.name} is {node.index_annot}")
