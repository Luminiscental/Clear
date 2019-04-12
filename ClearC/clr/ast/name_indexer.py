from collections import defaultdict
from clr.values import DEBUG
from clr.errors import emit_error
from clr.tokens import TokenType, token_info
from clr.ast.expression_nodes import IdentExpr
from clr.ast.visitor import StructTrackingDeclVisitor
from clr.ast.index_annotations import IndexAnnotation, IndexAnnotationType
from clr.ast.type_annotations import BUILTINS


class NameIndexer(StructTrackingDeclVisitor):
    def __init__(self):
        super().__init__()
        self.scopes = [defaultdict(IndexAnnotation)]
        self.level = 0
        self.local_index = 0
        self.global_index = 0
        self.is_function = False

    def lookup_name(self, name):
        lookback = 0
        # Keep looking back up to the global scope
        while lookback <= self.level:
            scope = self.scopes[self.level - lookback]
            lookback += 1
            # If the scope contains a resolved index for the name we're done
            if name in scope:
                result = scope[name]
                return result
        # If no resolved name was found the returned index is unresolved
        return IndexAnnotation()

    def _declare_new(self):
        if self.level > 0:
            idx = self.local_index
            self.local_index += 1
            kind = IndexAnnotationType.LOCAL
        else:
            idx = self.global_index
            self.global_index += 1
            kind = IndexAnnotationType.GLOBAL
        return IndexAnnotation(kind, idx)

    def _declare_name(self, name):
        prev = self.lookup_name(name)
        if prev.kind == IndexAnnotationType.UNRESOLVED:
            # If the name already was not found as already declared make it a new index
            result = self._declare_new()
        else:
            # If it was already declared use the old value directly
            result = IndexAnnotation(prev.kind, prev.value)
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

    def visit_binary_expr(self, node):
        if node.operator.token_type == TokenType.DOT:
            node.left.accept(self)
            struct = self.structs[node.left.type_annotation.identifier]
            field_names = [field_name.lexeme for (_, field_name) in struct]
            index = field_names.index(node.right.name.lexeme)
            node.right.index_annotation = IndexAnnotation(
                IndexAnnotationType.PROPERTY, index
            )
        else:
            super().visit_binary_expr(node)

    def visit_call_expr(self, node):
        if isinstance(node.target, IdentExpr) and node.target.name.lexeme in BUILTINS:
            # If it's a built-in don't call super as we don't want to lookup the name
            for arg in node.arguments:
                arg.accept(self)
        else:
            super().visit_call_expr(node)

    def visit_this_expr(self, node):
        super().visit_this_expr(node)
        node.index_annotation = IndexAnnotation(IndexAnnotationType.UPVALUE, 0)

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

    def _index_function(self, node, is_method=False):
        # If it's a method we don't associate it with a name so that it doesn't override anything
        # and isn't accessible as its own object
        node.index_annotation = (
            self._declare_new() if is_method else self._declare_name(node.name.lexeme)
        )
        function = FunctionNameIndexer(self, is_method)
        for _, name in node.params:
            function.add_param(name.lexeme)
        for decl in node.block.declarations:
            decl.accept(function)
        node.upvalues.extend(function.upvalues)
        self.errors.extend(function.errors)

    def visit_func_decl(self, node):
        # No super as we handle the params / scoping
        self._index_function(node)

    def visit_method_decl(self, node):
        # No super as we don't delegate to visit_func_decl
        self._index_function(node, is_method=True)

    def visit_struct_decl(self, node):
        super().visit_struct_decl(node)
        # Index the constructors references
        function = FunctionNameIndexer(self)
        for method in node.methods.values():
            method.constructor_index_annotation = function.lookup_index(
                method.index_annotation
            )
        # Declare the constructor
        node.index_annotation = self._declare_name(node.name.lexeme)
        node.upvalues.extend(function.upvalues)
        self.errors.extend(function.errors)


class FunctionNameIndexer(NameIndexer):
    def __init__(self, parent, is_method=False):
        super().__init__()
        # Inherit structs from parent as a copy
        self.structs = parent.structs.copy()
        self.parent = parent
        self.scopes.append(defaultdict(IndexAnnotation))
        # Default scope is not the global scope in a function
        self.level += 1
        self.params = []
        self.upvalues = []
        self.is_function = True
        self.is_method = is_method

    def add_param(self, name):
        index = len(self.params)
        pair = (name, IndexAnnotation(kind=IndexAnnotationType.PARAM, value=index))
        self.params.append(pair)

    def add_upvalue(self, index, name=""):
        if self.is_method:
            # TODO: Better reporting; maybe move to type resolver
            emit_error(
                f'Reference to value "{name}" is invalid within a method; methods can\'t have upvalues!'
            )()
        upvalue_index = len(self.upvalues)
        self.upvalues.append(index)
        return IndexAnnotation(IndexAnnotationType.UPVALUE, upvalue_index)

    def lookup_index(self, index, name=""):
        if index.kind == IndexAnnotationType.GLOBAL:
            # Globals can be referenced normally
            return index
        return self.add_upvalue(index, name)

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
                result = self.lookup_index(lookup, name)
        return result
