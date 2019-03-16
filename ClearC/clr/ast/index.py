from enum import Enum
from collections import defaultdict
from clr.ast.visitor import DeclVisitor
from clr.errors import ClrCompileError, emit_error
from clr.values import DEBUG
from clr.ast.resolve import BUILTINS


class Index(Enum):
    UNRESOLVED = "<unresolved>"
    PARAM = "<param>"
    LOCAL = "<local>"
    GLOBAL = "<global>"

    def __str__(self):
        return self.value


class IndexAnnotation:
    def __init__(self, kind=Index.UNRESOLVED, value=-1):
        self.kind = kind
        self.value = value

    def __repr__(self):
        return f"IndexAnnotation(kind={self.kind}, value={self.value})"


class Indexer(DeclVisitor):
    def __init__(self):
        self.scopes = [defaultdict(IndexAnnotation)]
        self.level = 0
        self.local_index = 0
        self.global_index = 0
        self.is_function = False

    def _lookup_name(self, name):
        lookback = 0
        while lookback < self.level:
            result = self.scopes[self.level - lookback][name]
            lookback += 1
            if result.kind != Index.UNRESOLVED:
                if DEBUG:
                    print(f"Found {name} with index {result}")
                break
        else:
            result = self.scopes[0][name]
            if DEBUG and result.kind != Index.UNRESOLVED:
                print(f"Looking for {name} in global scope results in {result}")
        return result

    def _declare_name(self, name):
        prev = self._lookup_name(name)
        if prev.kind == Index.UNRESOLVED:
            if self.level > 0:
                idx = self.local_index
                self.local_index += 1
                kind = Index.LOCAL
            else:
                idx = self.global_index
                self.global_index += 1
                kind = Index.GLOBAL
        else:
            idx = prev.value
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
        if self.level > 0:
            popped = self.scopes[self.level]
            popped_indices = [
                index for index in popped.values() if index.kind != Index.UNRESOLVED
            ]
            if popped_indices:
                self.local_index = min(map(lambda index: index.value, popped_indices))
                if DEBUG:
                    print(f"After popping local index is {self.local_index}")
        del self.scopes[self.level]
        self.level -= 1

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        if node.name.lexeme not in BUILTINS:
            node.index_annotation = self._lookup_name(node.name.lexeme)
            if node.index_annotation.kind == Index.UNRESOLVED:
                emit_error(f"Reference to undefined identifier! {node.get_info()}")()
            elif DEBUG:
                print(f"Set index for {node.get_info()} as {node.index_annotation}")

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        node.index_annotation = self._declare_name(node.name.lexeme)

    def visit_func_decl(self, node):
        # No super as we handle the params / scoping
        function = FunctionIndexer()
        for _, name in node.params:
            function.add_param(name.lexeme)
        for decl in node.block.declarations:
            decl.accept(function)
        node.index_annotation = self._declare_name(node.name.lexeme)


class FunctionIndexer(Indexer):
    def __init__(self):
        super().__init__()
        self.scopes.append(defaultdict(IndexAnnotation))
        self.level += 1
        self.params = []
        self.is_function = True

    def add_param(self, name):
        index = len(self.params)
        pair = (name, IndexAnnotation(kind=Index.PARAM, value=index))
        self.params.append(pair)

    def visit_ident_expr(self, node):
        try:
            super().visit_ident_expr(node)
        except ClrCompileError as undef_err:
            for param_name, param_index in self.params:
                if param_name == node.name.lexeme:
                    node.index_annotation = param_index
                    if DEBUG:
                        print(
                            f"Set index for {node.get_info()} as {node.index_annotation}"
                        )
                    break
            else:
                raise undef_err
