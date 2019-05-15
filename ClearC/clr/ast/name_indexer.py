from collections import OrderedDict, defaultdict
from clr.values import DEBUG
from clr.errors import emit_error
from clr.tokens import TokenType, token_info
from clr.ast.expression_nodes import IdentExpr
from clr.ast.visitor import StructTrackingDeclVisitor
from clr.ast.index_annotations import (
    IndexAnnotation,
    IndexAnnotationType,
    INDEX_OF_THIS,
)
from clr.ast.type_annotations import BUILTINS


class NameIndexer(StructTrackingDeclVisitor):
    def __init__(self):
        super().__init__()
        self.scopes = [defaultdict(IndexAnnotation)]
        self.scope_indices = [[]]
        self.level = 0
        self.local_index = 0
        self.global_index = 0
        self.is_function = False

    def increase_level(self):
        if DEBUG:
            print("Increasing scope level")
        self.scopes.append(defaultdict(IndexAnnotation))
        self.scope_indices.append([])
        self.level += 1

    def decrease_level(self):
        if DEBUG:
            print("Decreasing scope level")
        del self.scopes[self.level]
        del self.scope_indices[self.level]
        self.level -= 1

    def lookup_name(self, name):
        lookback = 0
        # Keep looking back up to the global scope
        while lookback <= self.level:
            scope = self.scopes[self.level - lookback]
            lookback += 1
            # If the scope contains a resolved index for the name we're done
            if name in scope:
                return scope[name]
        # If no resolved name was found the returned index is unresolved
        return IndexAnnotation()

    def _new_index(self):
        if self.level > 0:
            idx = self.local_index
            self.local_index += 1
            kind = IndexAnnotationType.LOCAL
        else:
            idx = self.global_index
            self.global_index += 1
            kind = IndexAnnotationType.GLOBAL
        result = IndexAnnotation(kind, idx)
        self.scope_indices[self.level].append(result)
        return result

    def _declare_name(self, name):
        result = self._new_index()
        self.scopes[self.level][name] = result
        if DEBUG:
            print(f"Declared {name} as {result}")
        return result

    def start_scope(self):
        super().start_scope()
        self.increase_level()

    def end_scope(self):
        super().end_scope()
        if self.level == 0:
            emit_error("Cannot end the global scope!")()
        else:
            popped_indices = self.scope_indices[self.level]
            # If there are resolved indices that went out of scope, reset back so that they can be
            # re-used
            if popped_indices:
                self.local_index = min(map(lambda index: index.value, popped_indices))
                if DEBUG:
                    print(f"After popping local index is {self.local_index}")
        self.decrease_level()

    def visit_access_expr(self, node):
        super().visit_access_expr(node)
        typename = node.left.type_annotation.identifier
        if typename in self.structs:
            struct = self.structs[typename]
        elif typename in self.props:
            struct = self.props[typename]
        field_names = [field_name.lexeme for (_, field_name) in struct.fields]
        index = field_names.index(node.right.name.lexeme)
        node.right.index_annotation = IndexAnnotation(
            IndexAnnotationType.PROPERTY, index
        )

    def visit_call_expr(self, node):
        if isinstance(node.target, IdentExpr) and node.target.name.lexeme in BUILTINS:
            # If it's a built-in don't call super as we don't want to lookup the name
            for arg in node.arguments:
                arg.accept(self)
        else:
            super().visit_call_expr(node)

    def visit_construct_expr(self, node):
        super().visit_construct_expr(node)
        # Lookup the constructor
        node.constructor_index_annotation = self.lookup_name(node.name.lexeme)
        struct = self.structs[node.name.lexeme]
        field_names = {}
        for i, field in enumerate(struct.fields):
            _, field_name = field
            field_names[field_name.lexeme] = i
        # Order the field specifiers so that they are in order to call the constructor
        node.args = OrderedDict(
            sorted(node.args.items(), key=lambda arg: field_names[arg[0]])
        )

    def visit_unpack_expr(self, node):
        node.target.accept(self)
        if node.present_value is not None:
            # Present case is actually a function over the target value
            implicit_function = FunctionNameIndexer(self)
            # Take the target value as a parameter, any other references become upvalues
            implicit_function.add_param(node.target.name.lexeme)
            node.present_value.accept(implicit_function)
            node.upvalues.extend(implicit_function.upvalues)
        if node.default_value is not None:
            node.default_value.accept(self)

    def visit_lambda_expr(self, node):
        # No super as we handle the params / scoping
        function = FunctionNameIndexer(self, False)
        for _, name in node.params:
            function.add_param(name.lexeme)
        node.result.accept(function)
        node.upvalues.extend(function.upvalues)
        self.errors.extend(function.errors)

    def visit_keyword_expr(self, node):
        super().visit_keyword_expr(node)
        if node.token.token_type == TokenType.THIS:
            node.index_annotation = self.lookup_name("this")

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
        if node.decorator:
            node.decorator.accept(self)
        # If it's a method we don't associate it with a name so that it doesn't override anything
        # and isn't accessible as its own object
        if not is_method:
            node.index_annotation = self._declare_name(node.name.lexeme)
        function = FunctionNameIndexer(self, is_method)
        if is_method:
            function.scopes[function.level]["this"] = IndexAnnotation(
                kind=IndexAnnotationType.UPVALUE, value=0
            )
            function.upvalues = [INDEX_OF_THIS]
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
        # Declare the methods before the constructor as they are created before it when compiling
        for method in node.methods.values():
            method.index_annotation = self._new_index()
            if method.decorator:
                method.decorator_index_annotation = self._new_index()
        # Declare the constructor before calling super() so that it can be referenced in methods
        node.index_annotation = self._declare_name(node.name.lexeme)
        # Call super(), visiting all the methods/fields
        super().visit_struct_decl(node)
        # Index the constructor's references
        constructor = FunctionNameIndexer(self)
        for method in node.methods.values():
            # Method upvalues are actually closed in the constructor,
            # so need indexed with the extra scope level accounted for.
            method.upvalues = method.upvalues[0:1] + [
                constructor.lookup_index(index) for index in method.upvalues[1:]
            ]
            # Similar for the actual index to get the method function object in the constructor
            method.constructor_index_annotation = constructor.lookup_index(
                method.index_annotation
            )
            if method.decorator:
                method.decorator_constructor_index_annotation = constructor.lookup_index(
                    method.decorator_index_annotation
                )
        node.upvalues.extend(constructor.upvalues)
        self.errors.extend(constructor.errors)


class FunctionNameIndexer(NameIndexer):
    def __init__(self, parent, is_method=False):
        super().__init__()
        # Inherit structs from parent as a copy
        self.structs = parent.structs.copy()
        self.props = parent.props.copy()
        self.parent = parent
        # Default scope is not the global scope in a function
        self.increase_level()
        self.params = []
        self.upvalues = []
        self.is_function = True
        self.is_method = is_method

    def add_param(self, name):
        index = len(self.params)
        pair = (name, IndexAnnotation(kind=IndexAnnotationType.PARAM, value=index))
        self.params.append(pair)

    def add_upvalue(self, index):
        upvalue_index = len(self.upvalues)
        self.upvalues.append(index)
        return IndexAnnotation(IndexAnnotationType.UPVALUE, upvalue_index)

    def lookup_index(self, index):
        if index.kind == IndexAnnotationType.GLOBAL:
            # Globals can be referenced normally
            return index
        return self.add_upvalue(index)

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
                result = self.lookup_index(lookup)
        # Update name lookup because upvalues don’t get added,
        # so it’s needed here to avoid making a new upvalue
        # for every reference to a variable.
        self.scopes[self.level][name] = result
        return result
