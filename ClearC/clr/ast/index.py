"""
This module provides an Indexer class for visiting AST nodes to index variable references to later
compile as bytecode.

Classes:
    - Index
    - IndexAnnotation
    - Indexer
    - FunctionIndexer
"""
from enum import Enum
from collections import defaultdict
from clr.ast.visitor import DeclVisitor
from clr.errors import ClrCompileError, emit_error
from clr.values import DEBUG
from clr.ast.resolve import BUILTINS


class Index(Enum):
    """
    This class enumerates possible types of variable indices.

    Superclasses:
        - Enum
    """

    UNRESOLVED = "<unresolved>"
    PARAM = "<param>"
    LOCAL = "<local>"
    GLOBAL = "<global>"

    def __str__(self):
        return self.value


class IndexAnnotation:
    """
    This class stores information about the annotated index for some AST node.

    Fields:
        - kind : the type of index
        - value : the integral value of the index
    """

    def __init__(self, kind=Index.UNRESOLVED, value=-1):
        self.kind = kind
        self.value = value

    def __repr__(self):
        return f"IndexAnnotation(kind={self.kind}, value={self.value})"


class Indexer(DeclVisitor):
    """
    This class is a DeclVisitor for walking over the AST, indexing declarations and annotating
    variable references with the indices they reference for use by the compiler.

    Superclasses:
        - DeclVisitor

    Fields:
        - scopes : a list of defaultdicts to annotations for looking up the annotation for a given
            name.
        - level : the current scope level to declare at.
        - local_index : the index of the next local variable to declare.
        - global_index : the index of the next global variable to declare.
        - is_function : boolean representing whether the current scope is within a function.
    """

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
            if result.kind != Index.UNRESOLVED:
                if DEBUG:
                    print(f"Found {name} with index {result}")
                break
        # If no resolved name was found the returned index is unresolved
        return result

    def _declare_name(self, name):
        prev = self.lookup_name(name)
        # If the name already was not found as already declared make it a new index
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
                index for index in popped.values() if index.kind != Index.UNRESOLVED
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
        if node.target.is_ident and node.target.name.lexeme in BUILTINS:
            # If it's a built-in don't call super as we don't want to lookup the name
            for arg in node.arguments:
                arg.accept(self)
        else:
            super().visit_call_expr(node)

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        node.index_annotation = self.lookup_name(node.name.lexeme)
        if node.index_annotation.kind == Index.UNRESOLVED:
            emit_error(f"Reference to undefined identifier! {node.get_info()}")()
        elif DEBUG:
            print(f"Set index for {node.get_info()} as {node.index_annotation}")

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        node.index_annotation = self._declare_name(node.name.lexeme)

    def visit_func_decl(self, node):
        # No super as we handle the params / scoping
        function = FunctionIndexer(self)
        for _, name in node.params:
            function.add_param(name.lexeme)
        for decl in node.block.declarations:
            decl.accept(function)
        node.index_annotation = self._declare_name(node.name.lexeme)


class FunctionIndexer(Indexer):
    """
    This class is an Indexer for indexing variable references within a function definition, so
    also allowing references to parameters.

    Superclasses:
        - Indexer

    Fields:
        - params : a list of (name, index) pairs for the parameter names and their index annotations.

    Methods:
        - add_param
    """

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.scopes.append(defaultdict(IndexAnnotation))
        # Default scope is not the global scope in a function
        self.level += 1
        self.params = []
        self.is_function = True

    def add_param(self, name):
        """
        This method adds a parameter of the given name to the function, with the indices of the
        parameters inferred from the order in which this is called.
        """
        index = len(self.params)
        pair = (name, IndexAnnotation(kind=Index.PARAM, value=index))
        self.params.append(pair)

    def lookup_name(self, name):
        result = super().lookup_name(name)
        if result.kind == Index.UNRESOLVED:
            # If it wasn't found look for it as a param
            for param_name, param_index in self.params:
                if param_name == name:
                    result = param_index
        if result.kind == Index.UNRESOLVED:
            # If it still isn't found look for it as an upvalue
            lookup = self.parent.lookup_name(name)
            if DEBUG:
                print(f"upvalue candidate: {lookup}")
            if lookup.kind == Index.GLOBAL:
                # globals can be referenced normally
                result = lookup
        return result
