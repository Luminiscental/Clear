import itertools
from collections import namedtuple, defaultdict
from clr.tokens import Token, TokenType, token_info
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
    NIL_TYPE,
    VOID_TYPE,
    IdentifierTypeAnnotation,
    FunctionTypeAnnotation,
    union_type,
)
from clr.ast.return_annotations import ReturnAnnotation, ReturnAnnotationType
from clr.ast.expression_nodes import (
    AccessExpr,
    KeywordExpr,
    IdentExpr,
    ARITHMETIC_OPS,
    EQUALITY_OPS,
    COMPARISON_OPS,
)
from clr.ast.statement_nodes import StmtNode, BlockStmt, ValDecl

TypeInfo = namedtuple(
    "TypeInfo", ("annotation", "assignable"), defaults=(TypeAnnotation(), False)
)


def check_name_collisions(fields):
    field_names = {}
    for _, field_name in fields:
        if field_name.lexeme in field_names:
            return field_name, field_names[field_name.lexeme]
        field_names[field_name.lexeme] = field_name
    return None


class TypeResolver(StructTrackingDeclVisitor):
    def __init__(self):
        super().__init__()
        self.scopes = [defaultdict(TypeInfo)]
        # TODO: Return type inference
        self.expected_returns = []
        self.level = 0
        self.current_structs = []

    def _declare_name(self, name, type_annotation, assignable=False, internal=False):
        if not internal and name.lexeme in self.scopes[self.level]:
            emit_error(f"Redeclaration of name {token_info(name)}!")()
        self.scopes[self.level][name.lexeme] = TypeInfo(type_annotation, assignable)

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
            and node.token.lexeme not in self.props
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
                    f"Invalid field assignment to {field_name} in struct constructor, "
                    f"`{node.name}` is not a field: `{node}`!"
                )()
            if not field_value.type_annotation.matches(
                field_names[field_name].as_annotation
            ):
                emit_error(
                    f"Incompatible type {field_value.type_annotation} for field {field_name} "
                    f"whose type is {field_names[field_name]}: `{node}`!"
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
                    f"Built-in function {token_info(node.target.name)} cannot take arguments of type "
                    f"{arg_string}: `{node}`!"
                )()
            node.type_annotation = builtin.return_type
        else:
            super().visit_call_expr(node)
            function_type = node.target.type_annotation
            if function_type.kind != TypeAnnotationType.FUNCTION:
                emit_error(
                    f"Attempt to call a non-callable expression `{node.target}`: "
                    f"`{node}`! (type is {function_type})"
                )()
            for i, (arg, param_type) in enumerate(
                zip(node.arguments, function_type.signature)
            ):
                if not arg.type_annotation.matches(param_type):
                    emit_error(
                        f"Incompatible type {arg.type_annotation} passed as argument {i+1}; "
                        f"expected {param_type}! `{node}`"
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
                f"Incompatible operand type {target_type} "
                f"for unary operator {token_info(node.operator)}: `{node}`!"
            )()
        node.type_annotation = target_type

    def visit_access_expr(self, node):
        super().visit_access_expr(node)
        if not isinstance(node.right, IdentExpr):
            emit_error(f"Accessor {node.right} is not an identifier! `{node}`")()
        property_token = node.right.name
        if node.left.type_annotation.kind != TypeAnnotationType.IDENTIFIER:
            emit_error(
                f"Non-struct type {node.left.type_annotation} does not have a property "
                f"{token_info(property_token)} to access: `{node}`!"
            )()
        typename = node.left.type_annotation.identifier
        if typename in self.structs:
            struct = self.structs[typename]
        else:
            struct = self.props[typename]
        fields = {
            field_name.lexeme: field_type for (field_type, field_name) in struct.fields
        }
        if property_token.lexeme not in fields:
            emit_error(
                f"No such property {token_info(property_token)} "
                f"on struct {node.left.type_annotation}: `{node}`"
            )()
        field_type = fields[property_token.lexeme]
        node.type_annotation = field_type.as_annotation

    def visit_binary_expr(self, node):
        super().visit_binary_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        unequal_err = emit_error(
            f"Incompatible operand types {left_type} and {right_type} "
            f"for binary operator {token_info(node.operator)}: `{node}`!"
        )
        if node.operator.token_type in ARITHMETIC_OPS:
            if left_type != right_type:
                unequal_err()
            if left_type not in ARITHMETIC_OPS[node.operator.token_type]:
                emit_error(
                    f"Incompatible operand type {left_type} "
                    f"for binary operator {token_info(node.operator)}: `{node}`!"
                )()
            node.type_annotation = left_type
        elif node.operator.token_type in COMPARISON_OPS:
            if left_type != right_type:
                unequal_err()
            if left_type not in [NUM_TYPE, INT_TYPE]:
                emit_error(
                    f"Incompatible operand type {left_type} "
                    f"for binary operator {token_info(node.operator)}: `{node}`!"
                )()
            node.type_annotation = BOOL_TYPE
        elif node.operator.token_type in EQUALITY_OPS:
            node.type_annotation = BOOL_TYPE
        else:
            emit_error(
                f"Unknown binary operator {token_info(node.operator)}: `{node}`!"
            )()

    def visit_unpack_expr(self, node):
        node.target.accept(self)
        if node.target.type_annotation.kind != TypeAnnotationType.OPTIONAL:
            emit_error(f"Cannot unpack non-optional value: `{node}`!")()
        if node.present_value is not None:
            orig_info = self._lookup_name(node.target.name.lexeme)
            self._declare_name(
                node.target.name,
                orig_info.annotation.target,
                orig_info.assignable,
                internal=True,
            )
            node.present_value.accept(self)
            self._declare_name(
                node.target.name,
                orig_info.annotation,
                orig_info.assignable,
                internal=True,
            )
        if node.default_value is not None:
            node.default_value.accept(self)
        # Both cases are present
        if node.present_value is not None and node.default_value is not None:
            union = union_type(
                node.present_value.type_annotation, node.default_value.type_annotation
            )
            if union is None:
                emit_error(
                    f"Incompatible types for branches of optional unpacking "
                    f"{node.present_value.type_annotation} and {node.default_value.type_annotation}: `{node}`!"
                )()
            node.type_annotation = union
        # Present-case only
        elif node.present_value is not None:
            node.type_annotation = VOID_TYPE
        # Default-case only
        elif node.default_value is not None:
            target_type = node.target.type_annotation.target
            if node.default_value.type_annotation == VOID_TYPE:
                node.type_annotation = VOID_TYPE
            elif node.default_value.type_annotation != target_type:
                emit_error(
                    f"Incompatible types for optional unpacking: "
                    f"{target_type} expected from implicit present case but the default case is of type "
                    f"{node.default_value.type_annotation}: `{node}`!"
                )()
            else:
                node.type_annotation = node.default_value.type_annotation

    def visit_lambda_expr(self, node):
        # No super as we handle parameter scoping
        self.start_scope()
        param_types = []
        for param_type, param_name in node.params:
            param_type.accept(self)
            resolved_type = param_type.as_annotation
            if resolved_type.kind == TypeAnnotationType.UNRESOLVED:
                emit_error(
                    f"Invalid parameter type {param_type} for function lambda: `{node}`!"
                )()
            self._declare_name(param_name, resolved_type)
            param_types.append(resolved_type)
        node.result.accept(self)
        self.end_scope()
        node.type_annotation = FunctionTypeAnnotation(
            return_type=node.result.type_annotation, signature=param_types
        )

    def visit_if_expr(self, node):
        super().visit_if_expr(node)
        expected_type = None
        for cond, value in node.checks:
            if not cond.type_annotation.matches(BOOL_TYPE):
                emit_error(
                    f"Incompatible condition type {cond.type_annotation} for if expression: `{node}`!"
                )()
            if expected_type is None:
                expected_type = value.type_annotation
            else:
                union = union_type(expected_type, value.type_annotation)
                if union is None:
                    emit_error(
                        f"Non-matching types in branches of if expression, "
                        f"expected {expected_type} but got {value.type_annotation}: `{node}`!"
                    )()
                expected_type = union
        union = union_type(expected_type, node.otherwise.type_annotation)
        if union is None:
            emit_error(
                f"Type for else branch of if expression {node.otherwise.type_annotation} "
                f"doesn't match expected type {expected_type}"
            )()
        node.type_annotation = union

    def visit_assign_expr(self, node):
        super().visit_assign_expr(node)
        if not node.left.assignable:
            emit_error(f"Unassignable expression `{node.left}`: `{node}`!")()
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if not right_type.matches(left_type):
            emit_error(
                f"`{node.left}` is of type {left_type}, so cannot assign `{node.right}` "
                f"of type {right_type} to it: `{node}`!"
            )()
        node.type_annotation = left_type

    def visit_and_expr(self, node):
        super().visit_and_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type != BOOL_TYPE:
            emit_error(
                f"Incompatible type {left_type} for left operand to logic operator "
                f"{token_info(node.operator)}: `{node}`!"
            )()
        if right_type != BOOL_TYPE:
            emit_error(
                f"Incompatible type {right_type} for right operand to logic operator "
                f"{token_info(node.operator)}: `{node}`!"
            )()
        node.type_annotation = BOOL_TYPE

    def visit_or_expr(self, node):
        super().visit_or_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type.kind == TypeAnnotationType.OPTIONAL:
            if not right_type.matches(left_type):
                emit_error(
                    f"Incompatible type {right_type} for optional unpacking of {left_type} "
                    f"in {token_info(node.operator)} expression: `{node}`!"
                )()
            node.type_annotation = left_type.target
        else:
            if not left_type.matches(BOOL_TYPE):
                emit_error(
                    f"Incompatible type {left_type} for left operand to logic operator "
                    f"{token_info(node.operator)}: `{node}`!"
                )()
            if not right_type.matches(BOOL_TYPE):
                emit_error(
                    f"Incompatible type {right_type} for right operand to logic operator "
                    f"{token_info(node.operator)}: `{node}`!"
                )()
            node.type_annotation = BOOL_TYPE

    def visit_keyword_expr(self, node):
        super().visit_keyword_expr(node)
        if node.token.token_type == TokenType.THIS:
            if not self.current_structs:
                emit_error(f"Cannot reference `this` outside of a method: `{node}`!")()
            else:
                node.type_annotation = IdentifierTypeAnnotation(
                    self.current_structs[-1].name.lexeme
                )
        elif node.token.token_type == TokenType.NIL:
            node.type_annotation = NIL_TYPE

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        if node.name.lexeme in BUILTINS:
            emit_error(
                f"Invalid identifier name {token_info(node.name)}: `{node}`! "
                f"This is reserved for the built-in function {node.name.lexeme}."
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
            if not node.value.type_annotation.matches(expected):
                emit_error(
                    f"Incompatible return type! Expected {expected} but was given "
                    f"{node.value.type_annotation} at {token_info(node.return_token)}!"
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
            if not cond.type_annotation.matches(BOOL_TYPE):
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
        self.resolve_function(node)

    def resolve_function(self, node, is_method=False):
        # Iterate over the parameters and resolve to types
        param_types = []
        for param_type, _ in node.params:
            param_type.accept(self)
            resolved_type = param_type.as_annotation
            if resolved_type.kind == TypeAnnotationType.UNRESOLVED:
                emit_error(
                    f"Invalid parameter type {param_type} for function {token_info(node.name)}!"
                )()
            param_types.append(resolved_type)
        # Resolve the return type
        node.return_type.accept(self)
        return_type = node.return_type.as_annotation
        # Create an annotation for the function signature
        node.type_annotation = FunctionTypeAnnotation(
            return_type=return_type, signature=param_types
        )
        if node.decorator:
            node.decorator.accept(self)
            decorator_type = node.decorator.type_annotation
            if decorator_type.kind != TypeAnnotationType.FUNCTION:
                emit_error(
                    f"Decorator must be a function, "
                    f"found {decorator_type} instead decorating {token_info(node.name)}!"
                )()
            if decorator_type.return_type.kind != TypeAnnotationType.FUNCTION:
                emit_error(
                    f"Decorator must produce a function, "
                    f"found {decorator_type.return_type} instead decorating {token_info(node.name)}!"
                )()
            pretty_sig = "(" + ", ".join(map(str, decorator_type.signature)) + ")"
            if len(decorator_type.signature) != 1:
                emit_error(
                    f"Decorator must have one parameter for the decorated function only, "
                    f"but actual signature is {pretty_sig} found decorating {token_info(node.name)}!"
                )()
            if decorator_type.signature[0] != node.type_annotation:
                emit_error(
                    f"Decorator expects function type {decorator_type.signature[0]} "
                    f"but the function {token_info(node.name)} has type {node.type_annotation}!"
                )()
            node.type_annotation = decorator_type.return_type
        # Declare the function
        if node.name.lexeme in self.structs:
            struct = self.structs[node.name.lexeme]
            emit_error(
                f"Cannot create function {token_info(node.name)} with same name as struct {token_info(struct.name)}!"
            )()
        elif node.name.lexeme in self.props:
            prop = self.props[node.name.lexeme]
            emit_error(
                f"Cannot create function {token_info(node.name)} with same name as property {token_info(prop.name)}!"
            )()
        # If it's not a method declare the function
        if not is_method:
            self._declare_name(node.name, node.type_annotation)
        # Start the function scope
        self.start_scope()
        # Iterate over the parameters and declare them
        for param_type, param_name in node.params:
            self._declare_name(param_name, param_type.as_annotation)
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

    def visit_method_decl(self, node):
        struct = self.current_structs[-1]
        this_token = Token(token_type=TokenType.THIS, lexeme="this", line=-1)
        prefixed_block = []
        for _, field_name in struct.fields:
            if field_name.lexeme in map(lambda pair: pair[1].lexeme, node.params):
                continue
            name_token = Token(
                token_type=TokenType.IDENTIFIER, lexeme=field_name.lexeme, line=-1
            )
            field_value = AccessExpr(KeywordExpr(this_token), IdentExpr(name_token))
            implicit_decl = ValDecl(False, name_token, None, field_value)
            prefixed_block.append(implicit_decl)
        prefixed_block.extend(node.block.declarations)
        node.block = BlockStmt(prefixed_block)
        self.resolve_function(node, is_method=True)

    def visit_prop_decl(self, node):
        super().visit_prop_decl(node)
        collision = check_name_collisions(node.fields)
        if collision is not None:
            duplicate, original = collision
            emit_error(
                f"Duplicate field {token_info(duplicate)} in property {token_info(node.name)}: "
                f"ambiguous with {token_info(original)}!"
            )()

    def visit_struct_decl(self, node):
        # Check before super() because super() adds it to self.structs
        name = node.name.lexeme
        if name in self.structs:
            # TODO: Point to previous definition
            emit_error(
                f"Redefinition of struct {node.name}! Struct shadowing is not allowed."
            )()
        # Check for name collisions
        collision = check_name_collisions(node.fields)
        if collision is not None:
            duplicate, original = collision
            emit_error(
                f"Duplicate field {token_info(duplicate)} in struct {token_info(node.name)}: "
                f"ambiguous with {token_info(original)}!"
            )()
        field_dict = {
            name_token.lexeme: type_node.as_annotation
            for type_node, name_token in node.fields
        }
        for prop_name in node.props:
            if prop_name not in self.props:
                emit_error(
                    f'Undefined property "{prop_name}" referenced for struct {token_info(node.name)}!'
                )
            prop = self.props[prop_name]
            field_map = node.props[prop_name]
            for type_node, name_token in prop.fields:
                field_name = name_token.lexeme
                field_type = type_node.as_annotation
                if field_name in field_map:
                    mapped_name = field_map[field_name]
                    if mapped_name not in field_dict:
                        emit_error(
                            f'Struct "{token_info(node.name)}" does not satisfy the property "{prop_name}", '
                            f'missing field "{field_name}={mapped_name}"; "{mapped_name}" not found!'
                        )()
                    found_type = field_dict[mapped_name]
                    if not found_type.matches(field_type):
                        emit_error(
                            f'Incompatible type {found_type} for property field "{field_name}={mapped_name}" '
                            f'of property "{prop_name}" in struct {token_info(node.name)}, expected {field_type}!'
                        )()
                else:
                    if field_name not in field_dict:
                        emit_error(
                            f'Struct "{token_info(node.name)}" does not satisfy the property "{prop_name}"; '
                            f'"{field_name}" not found!'
                        )()
                    found_type = field_dict[field_name]
                    if not found_type.matches(field_type):
                        emit_error(
                            f'Incompatible type {found_type} for property field "{field_name}" '
                            f'of property "{prop_name}" in struct {token_info(node.name)}, expected {field_type}!'
                        )()
        # Push the struct name onto self.current_structs
        self.current_structs.append(node)
        super().visit_struct_decl(node)
        # Pop it
        del self.current_structs[-1]
        node.type_annotation = IdentifierTypeAnnotation(name)

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        if node.type_description is not None:
            node.type_annotation = node.type_description.as_annotation
            if not node.initializer.type_annotation.matches(node.type_annotation):
                emit_error(
                    f"Incompatible initializing type `{node.initializer.type_annotation}` "
                    f"for variable {token_info(node.name)} declared as `{node.type_annotation}`!"
                )()
        else:
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
        self._declare_name(node.name, node.type_annotation, assignable=node.mutable)
