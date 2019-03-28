from collections import defaultdict
from clr.values import DEBUG
from clr.errors import emit_error
from clr.tokens import token_info
from clr.ast.expression_nodes import IdentExpr
from clr.ast.visitor import DeclVisitor
from clr.ast.index_annotations import IndexAnnotation, IndexAnnotationType
from clr.ast.type_annotations import BUILTINS


class NameIndexer(DeclVisitor):
    def __init__(self):
        self.scopes = [defaultdict(IndexAnnotation)]
        self.level = 0
        self.local_index = 0
        self.global_index = 0
        self.is_function = False

    def lookup_name(self, name):
        lookback = 0
        # Keep looking back up to the global scope
        while lookback <= self.level:
            result = self.scopes[self.level - lookback][name]
            lookback += 1
            # If the scope containes a resolved index for thei name we're done
            if result.kind != IndexAnnotationType.UNRESOLVED:
                if DEBUG:
                    print(f"Found {name} with index {result}")
                break
        # If no resolved name was found the returned index is unresolved
        return result

    def _declare_name(self, name):
        prev = self.lookup_name(name)
        # If the name already was not found as already declared make it a new index
        if prev.kind == IndexAnnotationType.UNRESOLVED:
            if self.level > 0:
                idx = self.local_index
                self.local_index += 1
                kind = IndexAnnotationType.LOCAL
            else:
                idx = self.global_index
                self.global_index += 1
                kind = IndexAnnotationType.GLOBAL
        else:
            # If it was already declared use the old value directly
            idx = prev.value
            kind = prev.kind
        result = IndexAnnotation(kind, idx)
        if DEBUG:
            print(f"Declared {name} as {result}")
        self.scopes[self.level][name] = result
        return result

    def start_scope(self):
        super().start_scope()
        self.scopes.append(defaultdict(IndexAnnotation))
        self.level += 1

    def end_scope(self):
        super().end_scope()
        if self.level == 0:
            emit_error("Cannot end the global scope!")()
        else:
            popped = self.scopes[self.level]
            popped_indices = [
                index
                for index in popped.values()
                if index.kind != IndexAnnotationType.UNRESOLVED
            ]
            # If there are resolved indices that went out of scope, reset back so that they can be
            # re-used
            if popped_indices:
                self.local_index = min(map(lambda index: index.value, popped_indices))
                if DEBUG:
                    print(f"After popping local index is {self.local_index}")
        # Remove the popped scope
        del self.scopes[self.level]
        self.level -= 1

    def visit_call_expr(self, node):
        if isinstance(node.target, IdentExpr) and node.target.name.lexeme in BUILTINS:
            # If it's a built-in don't call super as we don't want to lookup the name
            for arg in node.arguments:
                arg.accept(self)
        else:
            super().visit_call_expr(node)

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        node.index_annotation = self.lookup_name(node.name.lexeme)
        if node.index_annotation.kind == IndexAnnotationType.UNRESOLVED:
            emit_error(f"Reference to undefined identifier! {token_info(node.name)}")()
        elif DEBUG:
            print(f"Set index for {token_info(node.name)} as {node.index_annotation}")

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        node.index_annotation = self._declare_name(node.name.lexeme)

    def visit_func_decl(self, node):
        # No super as we handle the params / scoping
        node.index_annotation = self._declare_name(node.name.lexeme)
        function = FunctionNameIndexer(self)
        for _, name in node.params:
            function.add_param(name.lexeme)
        for decl in node.block.declarations:
            decl.accept(function)
        node.upvalues.extend(function.upvalues)


class FunctionNameIndexer(NameIndexer):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.scopes.append(defaultdict(IndexAnnotation))
        # Default scope is not the global scope in a function
        self.level += 1
        self.params = []
        self.upvalues = []
        self.is_function = True

    def add_param(self, name):
        index = len(self.params)
        pair = (name, IndexAnnotation(kind=IndexAnnotationType.PARAM, value=index))
        self.params.append(pair)

    def lookup_name(self, name):
        result = super().lookup_name(name)
        if result.kind == IndexAnnotationType.UNRESOLVED:
            # If it wasn't found look for it as a param
            for param_name, param_index in self.params:
                if param_name == name:
                    result = param_index
        if result.kind == IndexAnnotationType.UNRESOLVED:
            # If it still isn't found look for it as an upvalue
            lookup = self.parent.lookup_name(name)
            if lookup.kind != IndexAnnotationType.UNRESOLVED:
                if DEBUG:
                    print(f"upvalue candidate: {lookup}")
                if lookup.kind == IndexAnnotationType.GLOBAL:
                    # Globals can be referenced normally
                    result = lookup
                else:
                    upvalue_index = len(self.upvalues)
                    self.upvalues.append(lookup)
                    result = IndexAnnotation(IndexAnnotationType.UPVALUE, upvalue_index)
        return result
