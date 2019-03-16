from enum import Enum
import itertools
from collections import defaultdict
from clr.tokens import TokenType
from clr.errors import emit_error
from clr.ast.visitor import DeclVisitor


class Type(Enum):
    INT = "int"
    NUM = "num"
    STR = "str"
    BOOL = "bool"
    FUNCTION = "<function>"
    UNRESOLVED = "<unresolved>"

    def __str__(self):
        return self.value


class Return(Enum):
    NEVER = "<never>"
    SOMETIMES = "<sometimes>"
    ALWAYS = "<always>"

    def __str__(self):
        return self.value


class FuncInfo:
    def __init__(self, return_type, overloads):
        self.return_type = return_type
        self.overloads = overloads

    def __eq__(self, other):
        return (
            isinstance(other, FuncInfo)
            and self.return_type == other.return_type
            and self.overloads == other.overloads
        )


class TypeAnnotation:
    def __init__(self, kind=Type.UNRESOLVED, assignable=False, func_info=None):
        self.kind = kind
        if type(self.kind) == type(self):
            print(f"Created a weird kind!!!!!!!!!!!!!!!!!!")
        self.func_info = func_info
        self.assignable = assignable

    def __repr__(self):
        return str(self.kind)

    def __eq__(self, other):
        if not isinstance(other, TypeAnnotation):
            return False
        if self.kind != other.kind:
            return False
        if self.kind == Type.FUNCTION:
            return self.func_info == other.func_info
        return True


INT_TYPE = TypeAnnotation(kind=Type.INT)
NUM_TYPE = TypeAnnotation(kind=Type.NUM)
STR_TYPE = TypeAnnotation(kind=Type.STR)
BOOL_TYPE = TypeAnnotation(kind=Type.BOOL)

BUILTINS = {
    "type": TypeAnnotation(
        kind=Type.FUNCTION,
        func_info=FuncInfo(
            return_type=STR_TYPE,
            overloads=[[STR_TYPE], [INT_TYPE], [NUM_TYPE], [BOOL_TYPE]],
        ),
    ),
    "int": TypeAnnotation(
        kind=Type.FUNCTION,
        func_info=FuncInfo(
            return_type=INT_TYPE, overloads=[[INT_TYPE], [NUM_TYPE], [BOOL_TYPE]]
        ),
    ),
    "num": TypeAnnotation(
        kind=Type.FUNCTION,
        func_info=FuncInfo(
            return_type=NUM_TYPE, overloads=[[INT_TYPE], [NUM_TYPE], [BOOL_TYPE]]
        ),
    ),
    "bool": TypeAnnotation(
        kind=Type.FUNCTION,
        func_info=FuncInfo(
            return_type=BOOL_TYPE, overloads=[[INT_TYPE], [NUM_TYPE], [BOOL_TYPE]]
        ),
    ),
    "str": TypeAnnotation(
        kind=Type.FUNCTION,
        func_info=FuncInfo(
            return_type=STR_TYPE,
            overloads=[[STR_TYPE], [INT_TYPE], [NUM_TYPE], [BOOL_TYPE]],
        ),
    ),
}


class ReturnAnnotation:
    def __init__(self, kind=Return.NEVER, return_type=None):
        self.kind = kind
        self.return_type = return_type


class TypeResolver(DeclVisitor):
    def __init__(self):
        self.scopes = [defaultdict(TypeAnnotation)]
        self.expected_returns = []
        self.level = 0
        for builtin, builtin_type in BUILTINS.items():
            self._declare_name(builtin, builtin_type)

    def _declare_name(self, name, type_annotation):
        self.scopes[self.level][name] = type_annotation

    def _lookup_name(self, name):
        result = TypeAnnotation()
        lookback = 0
        while lookback <= self.level:
            result = self.scopes[self.level - lookback][name]
            lookback += 1
            if result.kind != Type.UNRESOLVED:
                break
        return result

    def start_scope(self):
        super().start_scope()
        self.scopes.append(defaultdict(TypeAnnotation))
        self.level += 1

    def end_scope(self):
        super().end_scope()
        del self.scopes[self.level]
        self.level -= 1

    def visit_call_expr(self, node):
        super().visit_call_expr(node)
        function_type = node.target.type_annotation
        if function_type.kind != Type.FUNCTION:
            emit_error(
                f"Attempt to call a non-callable object {node.target}! {node.get_info()}"
            )()
        passed_signature = list(map(lambda arg: arg.type_annotation, node.arguments))
        with_len = [
            overload
            for overload in function_type.func_info.overloads
            if len(overload) == len(passed_signature)
        ]
        if not with_len:
            possible_lens = (
                "["
                + ", ".join(
                    map(
                        lambda overload: str(len(overload)),
                        function_type.func_info.overloads,
                    )
                )
                + "]"
            )
            emit_error(
                f"No signature with matching number of passed arguments, found {len(passed_signature)} which is not one of the possibilities {possible_lens}! {node.get_info()}"
            )()
        for overload in with_len:
            if not overload == passed_signature:
                continue
            break
        else:
            args = "(" + ", ".join(map(str, passed_signature)) + ")"
            emit_error(
                f"Could not find signature for function matching provided argument list {args}! {node.get_info()}"
            )()
        node.type_annotation = function_type.func_info.return_type

    def visit_unary_expr(self, node):
        super().visit_unary_expr(node)
        target_type = node.target.type_annotation
        if (
            target_type.kind
            not in {TokenType.MINUS: [Type.NUM, Type.INT], TokenType.BANG: [Type.BOOL]}[
                node.operator.token_type
            ]
        ):
            emit_error(
                f"Incompatible operand type {target_type} for unary operator! {node.get_info()}"
            )()
        node.type_annotation = target_type

    def visit_binary_expr(self, node):
        super().visit_binary_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type.kind != right_type.kind:
            emit_error(
                f"Incompatible operand types {left_type} and {right_type} for binary operator! {node.get_info()}"
            )()
        arg_kind = left_type.kind
        if (
            arg_kind
            not in {
                TokenType.PLUS: [Type.NUM, Type.INT, Type.STR],
                TokenType.MINUS: [Type.NUM, Type.INT],
                TokenType.STAR: [Type.NUM, Type.INT],
                TokenType.SLASH: [Type.NUM],
                TokenType.EQUAL_EQUAL: Type,
                TokenType.BANG_EQUAL: Type,
                TokenType.LESS: [Type.NUM, Type.INT],
                TokenType.GREATER_EQUAL: [Type.NUM, Type.INT],
                TokenType.GREATER: [Type.NUM, Type.INT],
                TokenType.LESS_EQUAL: [Type.NUM, Type.INT],
                TokenType.EQUAL: Type,
            }[node.operator.token_type]
        ):
            emit_error(
                f"Incompatible operand type {arg_kind} for binary operator! {node.get_info()}"
            )()
        if node.operator.token_type == TokenType.EQUAL and not left_type.assignable:
            emit_error(f"Unassignable expression {node.left}! {node.get_info()}")()
        node.type_annotation = left_type

    def visit_and_expr(self, node):
        super().visit_and_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type.kind != Type.BOOL:
            emit_error(
                f"Incompatible type {left_type} for left operand to logic operator! {node.get_info()}"
            )()
        if right_type.kind != Type.BOOL:
            emit_error(
                f"Incompatible type {right_type} for right operand to logic operator! {node.get_info()}"
            )()

    def visit_or_expr(self, node):
        super().visit_or_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type.kind != Type.BOOL:
            emit_error(
                f"Incompatible type {left_type} for left operand to logic operator! {node.get_info()}"
            )()
        if right_type.kind != Type.BOOL:
            emit_error(
                f"Incompatible type {right_type} for right operand to logic operator! {node.get_info()}"
            )()

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        node.type_annotation = self._lookup_name(node.name.lexeme)
        if node.type_annotation.kind == Type.UNRESOLVED:
            emit_error(f"Reference to undefined identifier! {node.get_info()}")()

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
        kind = Return.NEVER
        return_type = None
        for decl in node.declarations:
            if kind == Return.ALWAYS:
                emit_error(f"Unreachable code! {decl.get_info()}")()
            annotation = decl.return_annotation
            if annotation.kind in [Return.SOMETIMES, Return.ALWAYS]:
                kind = annotation.kind
                return_type = annotation.return_type
        node.return_annotation = ReturnAnnotation(kind, return_type)

    def visit_ret_stmt(self, node):
        super().visit_ret_stmt(node)
        if not self.expected_returns:
            emit_error(
                f"Return statement found outside of function! {node.get_info()}"
            )()
        expected = self.expected_returns[-1]
        if expected.kind != Type.UNRESOLVED and expected != node.value.type_annotation:
            emit_error(
                f"Incompatible return type! Already expected {expected} but was given {node.value.type_annotation}! {node.get_info()}"
            )()
        expected = node.value.type_annotation
        node.return_annotation = ReturnAnnotation(Return.ALWAYS, expected)
        self.expected_returns[-1] = expected

    def visit_while_stmt(self, node):
        super().visit_while_stmt(node)
        node.return_annotation = node.block.return_annotation
        if node.return_annotation.kind == Return.ALWAYS:
            node.return_annotation.kind = Return.SOMETIMES

    def visit_if_stmt(self, node):
        super().visit_if_stmt(node)
        annotations = map(lambda pair: pair[1].return_annotation, node.checks)
        annotations = itertools.chain(
            annotations,
            [
                node.otherwise.return_annotation
                if node.otherwise is not None
                else ReturnAnnotation()
            ],
        )
        kind = Return.NEVER
        if all(map(lambda annotation: annotation.kind == Return.ALWAYS, annotations)):
            kind = Return.ALWAYS
        elif any(map(lambda annotation: annotation.kind != Return.NEVER, annotations)):
            kind = Return.SOMETIMES
        returns = [
            annotation.return_type
            for annotation in annotations
            if annotation.kind != Return.NEVER
        ]
        return_type = returns[0] if returns else None
        node.return_annotation = ReturnAnnotation(kind, return_type)

    def visit_func_decl(self, node):
        # No super because we handle the params
        self.start_scope()
        self.expected_returns.append(TypeAnnotation())
        arg_types = []
        for param_type, param_name in node.params:
            resolved_type = {
                "int": TypeAnnotation(kind=Type.INT),
                "num": TypeAnnotation(kind=Type.NUM),
                "str": TypeAnnotation(kind=Type.STR),
                "bool": TypeAnnotation(kind=Type.BOOL),
            }.get(param_type.lexeme, TypeAnnotation())
            if resolved_type.kind == Type.UNRESOLVED:
                emit_error(
                    f"Invalid parameter type {param_type} for function! {node.get_info()}"
                )()
            arg_types.append(resolved_type)
            self._declare_name(param_name.lexeme, resolved_type)
        node.block.accept(self)
        self.end_scope()
        del self.expected_returns[-1]
        if node.block.return_annotation.kind == Return.SOMETIMES:
            emit_error(f"Non-void function does not always return! {node.get_info()}")()
        # TODO: Lookup and add as an overload if already present
        func_info = FuncInfo(
            return_type=node.block.return_annotation.return_type, overloads=[arg_types]
        )
        type_annotation = TypeAnnotation(
            kind=Type.FUNCTION, assignable=False, func_info=func_info
        )
        self._declare_name(node.name.lexeme, type_annotation)

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        type_annotation = node.value.type_annotation
        type_annotation.assignable = node.mutable
        self._declare_name(node.name.lexeme, type_annotation)


###################################################################################################


# ResolvedName = namedtuple(
#    "ResolvedName",
#    ("value_type", "index", "is_global", "is_mutable", "is_param", "func_decl"),
#    defaults=(ValueType.UNRESOLVED, -1, False, False, False, None),
# )
#
#
# class Resolver(DeclVisitor):
#    def __init__(self):
#        self.scopes = [defaultdict(ResolvedName)]
#        self.level = 0
#        self.local_index = 0
#        self.global_index = 0
#        self.is_function = False
#
#    def _current_scope(self):
#        return self.scopes[self.level]
#
#    def _global_scope(self):
#        return self.scopes[0]
#
#    def _get_scope(self, lookback):
#        return self.scopes[self.level - lookback]
#
#    def _lookup_name(self, name):
#        result = ResolvedName()
#        lookback = 0
#        while lookback < self.level:
#            result = self._get_scope(lookback)[name]
#            lookback += 1
#            if result.value_type != ValueType.UNRESOLVED:
#                break
#        else:
#            result = self._global_scope()[name]
#        return result
#
#    def start_block_stmt(self, node):
#        super().start_block_stmt(node)
#        self.scopes.append(defaultdict(ResolvedName))
#        self.level += 1
#
#    def end_block_stmt(self, node):
#        super().end_block_stmt(node)
#        if self.level > 0:
#            popped = self._current_scope()
#            popped_indices = [r.index for r in popped.values() if r.index != -1]
#            if popped_indices:
#                self.local_index = min(popped_indices)
#        del self.scopes[self.level]
#        self.level -= 1
#        for decl in node.declarations:
#            if node.returns:
#                emit_error(f"Unreachable code! {decl.get_info()}")()
#            elif decl.returns:
#                node.returns = True
#
#    def _declare_name(self, name, value_type, is_mutable=False, func_decl=None):
#        prev = self._lookup_name(name)
#        if prev.value_type == ValueType.UNRESOLVED:
#            if self.level > 0:
#                idx = self.local_index
#                self.local_index += 1
#            else:
#                idx = self.global_index
#                self.global_index += 1
#        else:
#            idx = prev.index
#        result = ResolvedName(
#            value_type=value_type,
#            index=idx,
#            is_global=self.level == 0,
#            is_mutable=is_mutable,
#            func_decl=func_decl,
#        )
#        self._current_scope()[name] = result
#        return result
#
#    def visit_val_decl(self, node):
#        super().visit_val_decl(node)
#        node.resolved_name = self._declare_name(
#            node.name.lexeme, node.value.value_type, node.resolved_name.is_mutable
#        )
#
#    def visit_func_decl(self, node):
#        node.resolved_name = self._declare_name(
#            name=node.name.lexeme, value_type=ValueType.FUNCTION, func_decl=node
#        )
#        function = FunctionResolver()
#        for typename, name in node.params.pairs:
#            function.add_param(name.lexeme, typename.value_type)
#        for decl in node.block.declarations:
#            decl.accept(function)
#            if node.block.returns:
#                emit_error(f"Unreachable code! {decl.get_info()}")()
#            elif decl.returns:
#                node.block.returns = True
#        if not node.block.returns:
#            emit_error(f"Function may not return! {node.get_info()}")()
#        node.return_type = function.return_type
#        if DEBUG:
#            print(f"Function {node.get_info()} returns with {node.return_type}")
#
#    def visit_if_stmt(self, node):
#        super().visit_if_stmt(node)
#        node.returns = (
#            node.otherwise is not None
#            and node.otherwise.returns
#            and all(list(map(lambda check: check[1].returns, node.checks)))
#        )
#
#    def visit_ret_stmt(self, node):
#        super().visit_ret_stmt(node)
#        if not self.is_function:
#            emit_error(
#                f"Invalid return statement; must be inside a function! {node.get_info()}"
#            )()
#
#    def visit_unary_expr(self, node):
#        super().visit_unary_expr(node)
#        if (
#            node.target.value_type
#            not in {
#                TokenType.MINUS: [ValueType.NUM, ValueType.INT],
#                TokenType.BANG: [ValueType.BOOL],
#            }[node.operator.token_type]
#        ):
#            emit_error(
#                f"Incompatible type {str(node.target.value_type)} for unary operator {node.get_info()}!"
#            )()
#        node.value_type = node.target.value_type
#
#    def visit_binary_expr(self, node):
#        super().visit_binary_expr(node)
#        if node.left.value_type != node.right.value_type:
#            emit_error(
#                f"Incompatible operand types {str(node.left.value_type)} and {str(node.right.value_type)} for binary operator {node.get_info()}!"
#            )()
#        if (
#            node.left.value_type
#            not in {
#                TokenType.PLUS: [ValueType.NUM, ValueType.INT, ValueType.STR],
#                TokenType.MINUS: [ValueType.NUM, ValueType.INT],
#                TokenType.STAR: [ValueType.NUM, ValueType.INT],
#                TokenType.SLASH: [ValueType.NUM],
#                TokenType.EQUAL_EQUAL: ValueType,
#                TokenType.BANG_EQUAL: ValueType,
#                TokenType.LESS: [ValueType.NUM, ValueType.INT],
#                TokenType.GREATER_EQUAL: [ValueType.NUM, ValueType.INT],
#                TokenType.GREATER: [ValueType.NUM, ValueType.INT],
#                TokenType.LESS_EQUAL: [ValueType.NUM, ValueType.INT],
#                TokenType.EQUAL: ValueType,
#            }[node.operator.token_type]
#        ):
#            emit_error(
#                f"Incompatible type {str(node.left.value_type)} for binary operator {node.get_info()}!"
#            )()
#        if node.operator.token_type == TokenType.EQUAL and not node.left.is_assignable:
#            emit_error(
#                f"Unassignable expression {str(node.left)}! Attempt to assign at {node.get_info()}"
#            )()
#        node.value_type = node.left.value_type
#
#    def visit_call_expr(self, node):
#        super().visit_call_expr(node)
#        if node.target.value_type != ValueType.FUNCTION:
#            emit_error(
#                f"Attempt to call a non-callable object {str(node.target)}! Must be a function {node.get_info()}"
#            )()
#        function = node.target.resolved_name.func_decl
#        if len(function.params.pairs) != len(node.arguments):
#            emit_error(
#                f"Incorrect number of parameters! Expected {len(function.params.pairs)} found {len(node.arguments)}! {node.get_info()}"
#            )()
#        for i, pair in enumerate(function.params.pairs):
#            arg = node.arguments[i]
#            if pair[0].value_type != arg.value_type:
#                emit_error(
#                    f"Incorrect argument type at position {i}! Expected {pair[0].value_type} but found {arg.value_type}! {node.get_info()}"
#                )()
#        node.value_type = function.return_type
#
#    def visit_ident_expr(self, node):
#        super().visit_ident_expr(node)
#        node.resolved_name = self._lookup_name(node.name.lexeme)
#        if node.resolved_name.value_type == ValueType.UNRESOLVED:
#            emit_error(f"Reference to undefined identifier! {node.get_info()}")()
#        node.value_type = node.resolved_name.value_type
#        node.is_assignable = node.resolved_name.is_mutable
#        if DEBUG:
#            print(f"Value {node.get_info()} is found with type {node.value_type}")
#
#    def visit_builtin_expr(self, node):
#        super().visit_builtin_expr(node)
#        if (
#            node.target.value_type
#            not in {
#                TokenType.TYPE: ValueType,
#                TokenType.INT: [ValueType.NUM, ValueType.INT, ValueType.BOOL],
#                TokenType.BOOL: ValueType,
#                TokenType.NUM: [ValueType.NUM, ValueType.INT, ValueType.BOOL],
#                TokenType.STR: ValueType,
#            }[node.function.token_type]
#        ):
#            emit_error(
#                f"Incompatible parameter type {str(node.target.value_type)} for built-in function {node.get_info()}!"
#            )()
#
#    def visit_and_expr(self, node):
#        super().visit_and_expr(node)
#        if node.left.value_type != ValueType.BOOL:
#            emit_error(
#                f"Incompatible type {str(node.left.value_type)} for left operand to logic operator {node.get_info()}!"
#            )()
#        if node.right.value_type != ValueType.BOOL:
#            emit_error(
#                f"Incompatible type {str(node.right.value_type)} for right operand to logic operator {node.get_info()}!"
#            )()
#
#    def visit_or_expr(self, node):
#        super().visit_or_expr(node)
#        if node.left.value_type != ValueType.BOOL:
#            emit_error(
#                f"Incompatible type {str(node.left.value_type)} for left operand to logic operator {node.get_info()}!"
#            )()
#        if node.right.value_type != ValueType.BOOL:
#            emit_error(
#                f"Incompatible type {str(node.right.value_type)} for right operand to logic operator {node.get_info()}!"
#            )()
#
#
# class FunctionResolver(Resolver):
#    def __init__(self):
#        super().__init__()
#        self.scopes.append(defaultdict(ResolvedName))
#        self.level += 1
#        self.params = []
#        self.return_type = None
#        self.is_function = True
#
#    def add_param(self, name, value_type):
#        index = len(self.params)
#        self.params.append((name, value_type, index))
#
#    def visit_ret_stmt(self, node):
#        super().visit_ret_stmt(node)
#        return_type = self.return_type
#        if return_type is None:
#            self.return_type = node.value.value_type
#        else:
#            if return_type != node.value.value_type:
#                emit_error(
#                    f"Invalid return type! previously had {str(return_type)} but was given {str(node.value)} which is {str(node.value.value_type)}! {node.get_info()}"
#                )()
#        node.returns = True
#
#    def visit_ident_expr(self, node):
#        try:
#            super().visit_ident_expr(node)
#        except ClrCompileError:
#            for param_name, param_type, param_index in self.params:
#                if param_name == node.name.lexeme:
#                    node.resolved_name = ResolvedName(
#                        value_type=param_type, index=param_index, is_param=True
#                    )
#                    break
#            else:
#                emit_error(f"Reference to undefined identifier! {node.get_info()}")()
#        node.value_type = node.resolved_name.value_type
#        node.is_assignable = node.resolved_name.is_mutable
