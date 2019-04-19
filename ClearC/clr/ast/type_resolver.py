import itertools
from collections import namedtuple, defaultdict
from clr.tokens import TokenType, token_info
from clr.errors import emit_error
from clr.ast.visitor import StructTrackingDeclVisitor
from clr.ast.type_annotations import (
    TypeAnnotation,
    TypeAnnotationType,
    BUILTINS,
    NUM_TYPE,
    INT_TYPE,
    STR_TYPE,
    BOOL_TYPE,
    VOID_TYPE,
    ANY_TYPE,
    IdentifierTypeAnnotation,
    FunctionTypeAnnotation,
)
from clr.ast.return_annotations import ReturnAnnotation, ReturnAnnotationType
from clr.ast.expression_nodes import IdentExpr
from clr.ast.statement_nodes import StmtNode

TypeInfo = namedtuple(
    "TypeInfo", ("annotation", "assignable"), defaults=(TypeAnnotation(), False)
)


class TypeResolver(StructTrackingDeclVisitor):
    def __init__(self):
        super().__init__()
        self.scopes = [defaultdict(TypeInfo)]
        self.expected_returns = []
        self.level = 0
        self.current_structs = []

    def _declare_name(self, name, type_annotation, assignable=False):
        self.scopes[self.level][name] = TypeInfo(type_annotation, assignable)

    def _lookup_name(self, name):
        result = TypeInfo()
        lookback = 0
        while lookback <= self.level:
            result = self.scopes[self.level - lookback][name]
            lookback += 1
            if result.annotation.kind != TypeAnnotationType.UNRESOLVED:
                break
        return result

    def start_scope(self):
        super().start_scope()
        self.scopes.append(defaultdict(TypeInfo))
        self.level += 1

    def end_scope(self):
        super().end_scope()
        del self.scopes[self.level]
        self.level -= 1

    def visit_simple_type(self, node):
        if (
            node.as_annotation.kind == TypeAnnotationType.IDENTIFIER
            and node.token.lexeme not in self.structs
        ):
            emit_error(
                f"Reference to undefined type `{node}`! {token_info(node.token)}"
            )()

    def visit_construct_expr(self, node):
        super().visit_construct_expr(node)
        if node.name.lexeme not in self.structs:
            emit_error(f"No such struct `{node.name}`: `{node}`!")()
        struct = self.structs[node.name.lexeme]
        node.type_annotation = IdentifierTypeAnnotation(node.name.lexeme)
        specified_fields = set()
        field_names = {
            field_name.lexeme: field_type
            for i, (field_type, field_name) in enumerate(struct.fields)
            if i not in struct.methods
        }
        for field_name, field_value in node.args.items():
            if field_name not in field_names:
                emit_error(
                    f"Invalid field assignment to {field_name} in struct constructor, `{node.name}` is not a field: `{node}`!"
                )()
            if field_value.type_annotation != field_names[field_name].as_annotation:
                emit_error(
                    f"Incompatible type {field_value.type_annotation} for field {field_name} whose type is {field_names[field_name]}: `{node}`!"
                )()
            specified_fields.add(field_name)
        for field_name in field_names:
            if field_name not in specified_fields:
                emit_error(
                    f"Field {field_name} of {token_info(node.name)} was not specified in constructor: `{node}`!"
                )()

    def visit_call_expr(self, node):
        if isinstance(node.target, IdentExpr) and node.target.name.lexeme in BUILTINS:
            # If it's a built-in don't call super() as we don't evaluate the target
            for arg in node.arguments:
                arg.accept(self)
            builtin = BUILTINS[node.target.name.lexeme]
            type_list = list(map(lambda pair: pair.type_annotation, node.arguments))
            arg_string = "(" + ", ".join(map(str, type_list)) + ")"
            if type_list not in builtin.signatures:
                emit_error(
                    f"Built-in function {token_info(node.target.name)} cannot take arguments of type {arg_string}: `{node}`!"
                )()
            node.type_annotation = builtin.return_type
        else:
            super().visit_call_expr(node)
            function_type = node.target.type_annotation
            if function_type.kind != TypeAnnotationType.FUNCTION:
                emit_error(
                    f"Attempt to call a non-callable expression `{node.target}`: `{node}`! (type is {function_type})"
                )()
            passed_signature = list(
                map(lambda arg: arg.type_annotation, node.arguments)
            )
            args = "(" + ", ".join(map(str, passed_signature)) + ")"
            if passed_signature != function_type.signature:
                emit_error(
                    f"Could not find signature for function `{node.target}` matching provided argument list {args}: `{node}`!"
                )()
            node.type_annotation = function_type.return_type

    def visit_unary_expr(self, node):
        super().visit_unary_expr(node)
        target_type = node.target.type_annotation
        if (
            target_type
            not in {TokenType.MINUS: [NUM_TYPE, INT_TYPE], TokenType.BANG: [BOOL_TYPE]}[
                node.operator.token_type
            ]
        ):
            emit_error(
                f"Incompatible operand type {target_type} for unary operator {token_info(node.operator)}: `{node}`!"
            )()
        node.type_annotation = target_type

    def visit_access_expr(self, node):
        super().visit_access_expr(node)
        if node.left.type_annotation.kind != TypeAnnotationType.IDENTIFIER:
            emit_error(
                f"Non-struct type {node.left.type_annotation} does not have a property to access at {token_info(node.operator)}: `{node}`!"
            )()
        if not isinstance(node.right, IdentExpr):
            emit_error(f"Accessor {node.right} is not an identifier! `{node}`")()
        property_token = node.right.name
        struct = self.structs[node.left.type_annotation.identifier]
        fields = {
            field_name.lexeme: field_type for (field_type, field_name) in struct.fields
        }
        if property_token.lexeme not in fields:
            emit_error(
                f"No such property {token_info(property_token)} on struct {node.left.type_annotation}: `{node}`"
            )()
        field_type = fields[property_token.lexeme]
        node.type_annotation = field_type.as_annotation

    def visit_binary_expr(self, node):
        super().visit_binary_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type.kind != right_type.kind:
            emit_error(
                f"Incompatible operand types {left_type} and {right_type} for binary operator {token_info(node.operator)}: `{node}`!"
            )()
        if left_type == VOID_TYPE:
            emit_error(
                f"Cannot use call to void function `{node.left}` in expression: `{node}`!"
            )
        if (
            left_type
            not in {
                TokenType.PLUS: [NUM_TYPE, INT_TYPE, STR_TYPE],
                TokenType.MINUS: [NUM_TYPE, INT_TYPE],
                TokenType.STAR: [NUM_TYPE, INT_TYPE],
                TokenType.SLASH: [NUM_TYPE],
                TokenType.EQUAL_EQUAL: ANY_TYPE,
                TokenType.BANG_EQUAL: ANY_TYPE,
                TokenType.LESS: [NUM_TYPE, INT_TYPE],
                TokenType.GREATER_EQUAL: [NUM_TYPE, INT_TYPE],
                TokenType.GREATER: [NUM_TYPE, INT_TYPE],
                TokenType.LESS_EQUAL: [NUM_TYPE, INT_TYPE],
            }[node.operator.token_type]
        ):
            emit_error(
                f"Incompatible operand type {left_type} for binary operator {token_info(node.operator)}: `{node}`!"
            )()
        if node.operator.token_type in {
            TokenType.PLUS,
            TokenType.MINUS,
            TokenType.STAR,
            TokenType.SLASH,
            TokenType.BANG,
        }:
            node.type_annotation = left_type
        elif node.operator.token_type in {
            TokenType.EQUAL_EQUAL,
            TokenType.BANG_EQUAL,
            TokenType.GREATER,
            TokenType.GREATER_EQUAL,
            TokenType.LESS,
            TokenType.LESS_EQUAL,
        }:
            node.type_annotation = BOOL_TYPE

    def visit_assign_expr(self, node):
        super().visit_assign_expr(node)
        if not node.left.assignable:
            emit_error(f"Unassignable expression `{node.left}`: `{node}`!")()
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type.kind != right_type.kind:
            emit_error(
                f"`{node.left}` is of type {left_type}, so cannot assign `{node.right}` of type {right_type} to it: `{node}`!"
            )()
        node.type_annotation = left_type

    def visit_and_expr(self, node):
        super().visit_and_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type != BOOL_TYPE:
            emit_error(
                f"Incompatible type {left_type} for left operand to logic operator {token_info(node.operator)}: `{node}`!"
            )()
        if right_type != BOOL_TYPE:
            emit_error(
                f"Incompatible type {right_type} for right operand to logic operator {token_info(node.operator)}: `{node}`!"
            )()

    def visit_or_expr(self, node):
        super().visit_or_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type != BOOL_TYPE:
            emit_error(
                f"Incompatible type {left_type} for left operand to logic operator {token_info(node.operator)}: `{node}`!"
            )()
        if right_type != BOOL_TYPE:
            emit_error(
                f"Incompatible type {right_type} for right operand to logic operator {token_info(node.operator)}: `{node}`!"
            )()

    def visit_this_expr(self, node):
        super().visit_this_expr(node)
        if not self.current_structs:
            emit_error(f"Cannot reference `this` outside of a method: `{node}`!")()
        else:
            node.type_annotation = IdentifierTypeAnnotation(self.current_structs[-1])

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        if node.name.lexeme in BUILTINS:
            emit_error(
                f"Invalid identifier name {token_info(node.name)}: `{node}`! This is reserved for the built-in function {node.name.lexeme}."
            )()
        (node.type_annotation, node.assignable) = self._lookup_name(node.name.lexeme)
        if node.type_annotation.kind == TypeAnnotationType.UNRESOLVED:
            err_msg = (
                f"Reference to undefined identifier {token_info(node.name)}: `{node}`!"
            )
            if node.name.lexeme in self.structs:
                err_msg += (
                    f"\nMaybe you meant to use a construct expression? e.g. `{node.name.lexeme}"
                    " { ... }`"
                )
            emit_error(err_msg)()

    def visit_string_expr(self, node):
        super().visit_string_expr(node)
        node.type_annotation = STR_TYPE

    def visit_number_expr(self, node):
        super().visit_number_expr(node)
        node.type_annotation = INT_TYPE if node.integral else NUM_TYPE

    def visit_boolean_expr(self, node):
        super().visit_boolean_expr(node)
        node.type_annotation = BOOL_TYPE

    def visit_block_stmt(self, node):
        super().visit_block_stmt(node)
        kind = ReturnAnnotationType.NEVER
        return_type = None
        for decl in node.declarations:
            if kind == ReturnAnnotationType.ALWAYS:
                emit_error(f"Unreachable code {token_info(decl.first_token)}!")()
            if not isinstance(decl, StmtNode):
                continue
            annotation = decl.return_annotation
            if annotation.kind in [
                ReturnAnnotationType.SOMETIMES,
                ReturnAnnotationType.ALWAYS,
            ]:
                kind = annotation.kind
                return_type = annotation.return_type
        node.return_annotation = ReturnAnnotation(kind, return_type)

    def visit_ret_stmt(self, node):
        super().visit_ret_stmt(node)
        if not self.expected_returns:
            emit_error(
                f"Return statement found outside of function {token_info(node.return_token)}!"
            )()
        expected = self.expected_returns[-1]
        if node.value is None:
            if expected != VOID_TYPE:
                emit_error(
                    f"Missing return value for return statement in non-void function {token_info(node.return_token)}!"
                )
        else:
            if expected == VOID_TYPE:
                emit_error(
                    f"Return statement found in void function {token_info(node.return_token)}!"
                )()
            if expected != node.value.type_annotation:
                emit_error(
                    f"Incompatible return type! Expected {expected} but was given {node.value.type_annotation} at {token_info(node.return_token)}!"
                )()
        node.return_annotation = ReturnAnnotation(ReturnAnnotationType.ALWAYS, expected)

    def visit_while_stmt(self, node):
        super().visit_while_stmt(node)
        node.return_annotation = node.block.return_annotation
        if node.return_annotation.kind == ReturnAnnotationType.ALWAYS:
            node.return_annotation.kind = ReturnAnnotationType.SOMETIMES

    def visit_if_stmt(self, node):
        super().visit_if_stmt(node)
        for cond, _ in node.checks:
            if cond.type_annotation != BOOL_TYPE:
                emit_error(
                    f"Expected boolean condition for if-block but got {cond.type_annotation} instead: `{cond}`!"
                )()
        annotations = map(lambda pair: pair[1].return_annotation, node.checks)
        annotations = itertools.chain(
            annotations,
            [
                node.otherwise.return_annotation
                if node.otherwise is not None
                else ReturnAnnotation()
            ],
        )
        kind = ReturnAnnotationType.NEVER
        if all(
            map(
                lambda annotation: annotation.kind == ReturnAnnotationType.ALWAYS,
                annotations,
            )
        ):
            kind = ReturnAnnotationType.ALWAYS
        elif any(
            map(
                lambda annotation: annotation.kind != ReturnAnnotationType.NEVER,
                annotations,
            )
        ):
            kind = ReturnAnnotationType.SOMETIMES
        returns = [
            annotation.return_type
            for annotation in annotations
            if annotation.kind != ReturnAnnotationType.NEVER
        ]
        return_type = returns[0] if returns else None
        node.return_annotation = ReturnAnnotation(kind, return_type)

    def visit_func_decl(self, node):
        # No super because we handle the params
        # Iterate over the parameters and resolve to types
        arg_types = []
        for param_type, param_name in node.params:
            param_type.accept(self)
            resolved_type = param_type.as_annotation
            if resolved_type.kind == TypeAnnotationType.UNRESOLVED:
                emit_error(
                    f"Invalid parameter type {param_type} for function {token_info(node.name)}!"
                )()
            arg_types.append(resolved_type)
        # Resolve the return type
        node.return_type.accept(self)
        return_type = node.return_type.as_annotation
        # Create an annotation for the function signature
        node.type_annotation = FunctionTypeAnnotation(
            return_type=return_type, signature=arg_types
        )
        # Declare the function
        if node.name.lexeme in self.structs:
            struct = self.structs[node.name.lexeme]
            emit_error(
                f"Cannot create function {token_info(node.name)} with same name as struct {token_info(struct.name)}!"
            )()
        self._declare_name(node.name.lexeme, node.type_annotation)
        # Start the function scope
        self.start_scope()
        # Iterate over the parameters and declare them
        for param_type, param_name in node.params:
            self._declare_name(param_name.lexeme, param_type.as_annotation)
        # Expect return statements for the return type
        self.expected_returns.append(return_type)
        # Define the function by its block
        node.block.accept(self)
        # End the function scope
        self.end_scope()
        # Stop expecting return statements
        del self.expected_returns[-1]
        if (
            return_type != VOID_TYPE
            and node.block.return_annotation.kind != ReturnAnnotationType.ALWAYS
        ):
            emit_error(f"Function does not always return {token_info(node.name)}!")()

    def visit_struct_decl(self, node):
        # Check before super() because super() adds it to self.structs
        name = node.name.lexeme
        if name in self.structs:
            # TODO: Point to previous definition
            emit_error(
                f"Redefinition of struct {node.name}! Struct shadowing is not allowed."
            )()
        # Check for name collisions
        field_names = {}
        for _, field_name in node.fields:
            if field_name.lexeme in field_names:
                emit_error(
                    f"Duplicate field {token_info(field_name)} in struct {token_info(node.name)}: "
                    f"ambiguous with {token_info(field_names[field_name.lexeme])}!"
                )()
            field_names[field_name.lexeme] = field_name
        # Push the struct name onto self.current_structs
        self.current_structs.append(node.name.lexeme)
        super().visit_struct_decl(node)
        # Pop it
        del self.current_structs[-1]
        node.type_annotation = IdentifierTypeAnnotation(name)

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        node.type_annotation = node.initializer.type_annotation
        if node.type_annotation == VOID_TYPE:
            emit_error(
                f"Cannot create variable {token_info(node.name)} from calling void function `{node.initializer}`!"
            )()
        if node.name.lexeme in self.structs:
            struct = self.structs[node.name.lexeme]
            emit_error(
                f"Cannot create variable {token_info(node.name)} with same name as struct {token_info(struct.name)}!"
            )()
        self._declare_name(
            node.name.lexeme, node.type_annotation, assignable=node.mutable
        )
