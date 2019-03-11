"""
This module provides a Compiler class for visiting an AST
and generating bytecode along with a Program class to handle
the low-level parts of generating that bytecode.
"""
from clr.errors import emit_error
from clr.assemble import assembled_size
from clr.constants import Constants, ClrUint
from clr.values import OpCode, DEBUG
from clr.tokens import TokenType, token_info
from clr.visitor import AstVisitor


class Program:
    """
    This class wraps a list of bytecode with methods to handle simple operations such as
    defining variables / pushing one-ops.
    """

    def __init__(self):
        self.code_list = []

    def load_constant(self, constant):
        """
        This function emits bytecode to load the constant at the given index.
        """
        self.code_list.append(OpCode.LOAD_CONST)
        self.code_list.append(constant)

    def simple_op(self, opcode):
        """
        This function emits a single given opcode.
        """
        self.code_list.append(opcode)

    def define_name(self, resolved_name):
        """
        This function emits bytecode to define a given name that has been resolved.
        """
        if resolved_name.is_global:
            self.code_list.append(OpCode.DEFINE_GLOBAL)
        else:
            self.code_list.append(OpCode.DEFINE_LOCAL)
        self.code_list.append(resolved_name.index)

    def set_name(self, resolved_name):
        """
        This function emits bytecode to update the value of a given name that has been resolved.
        """
        if resolved_name.is_global:
            self.code_list.append(OpCode.DEFINE_GLOBAL)
        else:
            self.code_list.append(OpCode.DEFINE_LOCAL)
        self.code_list.append(resolved_name.index)

    def load_name(self, resolved_name):
        """
        This function emits bytecode to load a given name that has been resolved.
        """
        self.code_list.append(
            OpCode.LOAD_GLOBAL if resolved_name.is_global else OpCode.LOAD_LOCAL
        )
        self.code_list.append(resolved_name.index)

    def begin_jump(self, conditional=False, leave_value=False):
        """
        This function emits bytecode to emit an optionally conditional jump,
        returning an index to later patch the offset to jump by.
        """
        self.code_list.append(OpCode.JUMP_IF_NOT if conditional else OpCode.JUMP)
        index = len(self.code_list)
        if DEBUG:
            print(f"Defining a jump from {index}")
        temp_offset = ClrUint(0)
        self.code_list.append(temp_offset)
        if conditional and not leave_value:
            self.code_list.append(OpCode.POP)
        return index, conditional

    def end_jump(self, jump_ref, leave_value=False):
        """
        This function accepts an index to a previously emitted jump
        to patch its offset to jump to the current position.
        """
        index, conditional = jump_ref
        contained = self.code_list[index + 1 :]
        offset = assembled_size(contained)
        if DEBUG:
            print(f"Jump from {index} set with offset {offset}")
        self.code_list[index] = ClrUint(offset)
        if conditional and not leave_value:
            self.code_list.append(OpCode.POP)

    def flush(self):
        """
        This function returns the list of bytecode that has been emitted.
        """
        return self.code_list


class Compiler(AstVisitor):
    """
    This class provides functionality used for visiting AST nodes to generate bytecode.
    """

    def __init__(self):
        self.program = Program()
        self.constants = Constants()

    def flush_code(self):
        """
        This function returns the bytecode of the program containing both
        constant definitions and actual operations.
        """
        return self.constants.flush() + self.program.flush()

    def visit_val_decl(self, node):
        """
        This function emits bytecode to initialize a resolved name with
        the value of a given expression.
        """
        self.program.define_name(node.resolved_name)

    def visit_print_stmt(self, node):
        """
        This function emits bytecode to print the value of an expression;
        or print a blank line if the expression is None.
        """
        if node.value is None:
            self.program.simple_op(OpCode.PRINT_BLANK)
        else:
            self.program.simple_op(OpCode.PRINT)

    def visit_if_stmt(self, node):
        """
        This function takes a list of condition expressions and blocks to execute
        for each condition and emits bytecode to execute the first block with a
        satisified condition or a final block otherwise.
        """
        final_jumps = []
        for cond, block in node.checks:
            cond.accept(self)
            jump = self.program.begin_jump(conditional=True)
            block.accept(self)
            final_jumps.append(self.program.begin_jump())
            self.program.end_jump(jump)
        if node.otherwise is not None:
            node.otherwise.accept(self)
        for final_jump in final_jumps:
            self.program.end_jump(final_jump)

    def visit_expr_stmt(self, node):
        """
        This function emits bytecode to evaluate and then drop the result of an expression.
        """
        self.program.simple_op(OpCode.POP)

    def start_block_stmt(self, node):
        """
        This function emits bytecode to push a new scope.
        """
        self.program.simple_op(OpCode.PUSH_SCOPE)

    def end_block_stmt(self, node):
        """
        This function emits bytecode to pop the current scope.
        """
        self.program.simple_op(OpCode.POP_SCOPE)

    def visit_unary_expr(self, node):
        """
        This function emits bytecode to apply a unary operator to the result of an expression.
        """
        {
            TokenType.MINUS: lambda: self.program.simple_op(OpCode.NEGATE),
            TokenType.BANG: lambda: self.program.simple_op(OpCode.NOT),
        }.get(
            node.operator.token_type,
            emit_error(f"Unknown unary operator! {token_info(node.operator)}"),
        )()

    def visit_binary_expr(self, node):
        """
        This function emits bytecode to apply a binary operator to the result
        of two expressions.
        """
        if node.operator.token_type == TokenType.EQUAL:
            self.program.set_name(node.left.resolved_name)
            self.program.simple_op(OpCode.POP)
            self.program.load_name(node.left.resolved_name)
        else:
            {
                TokenType.PLUS: lambda: self.program.simple_op(OpCode.ADD),
                TokenType.MINUS: lambda: self.program.simple_op(OpCode.SUBTRACT),
                TokenType.STAR: lambda: self.program.simple_op(OpCode.MULTIPLY),
                TokenType.SLASH: lambda: self.program.simple_op(OpCode.DIVIDE),
                TokenType.EQUAL_EQUAL: lambda: self.program.simple_op(OpCode.EQUAL),
                TokenType.BANG_EQUAL: lambda: self.program.simple_op(OpCode.NEQUAL),
                TokenType.LESS: lambda: self.program.simple_op(OpCode.LESS),
                TokenType.GREATER_EQUAL: lambda: self.program.simple_op(OpCode.NLESS),
                TokenType.GREATER: lambda: self.program.simple_op(OpCode.GREATER),
                TokenType.LESS_EQUAL: lambda: self.program.simple_op(OpCode.NGREATER),
            }.get(
                node.operator.token_type,
                emit_error(f"Unknown binary operator! {token_info(node.operator)}"),
            )()

    def visit_constant_expr(self, node):
        """
        This function emits bytecode to load a value as a constant.
        """
        const_index = self.constants.add(node.value)
        self.program.load_constant(const_index)

    def visit_boolean_expr(self, node):
        """
        This function emits bytecode to load a boolean value.
        """
        self.program.simple_op(OpCode.TRUE if node.value else OpCode.FALSE)

    def visit_ident_expr(self, node):
        """
        This function emits bytecode to load the value of a resolved identifier.
        """
        self.program.load_name(node.resolved_name)

    def visit_builtin_expr(self, node):
        """
        This function emits bytecode to apply a builtin function to the value of an expression.
        """
        {
            TokenType.TYPE: lambda: self.program.simple_op(OpCode.TYPE),
            TokenType.INT: lambda: self.program.simple_op(OpCode.INT),
            TokenType.BOOL: lambda: self.program.simple_op(OpCode.BOOL),
            TokenType.NUM: lambda: self.program.simple_op(OpCode.NUM),
            TokenType.STR: lambda: self.program.simple_op(OpCode.STR),
        }.get(
            node.function.token_type,
            emit_error(f"Expected built-in function! {token_info(node.function)}"),
        )()

    def visit_and_expr(self, node):
        """
        This funcction emits bytecode to apply the logical "and" operator to the result of
        two expressions.
        """
        node.left.accept(self)
        short_circuit = self.program.begin_jump(conditional=True)
        node.right.accept(self)
        self.program.end_jump(short_circuit, leave_value=True)

    def visit_or_expr(self, node):
        """
        This funcction emits bytecode to apply the logical "or" operator to the result of
        two expressions.
        """
        node.left.accept(self)
        long_circuit = self.program.begin_jump(conditional=True, leave_value=True)
        short_circuit = self.program.begin_jump()
        self.program.end_jump(long_circuit)
        node.right.accept(self)
        self.program.end_jump(short_circuit, leave_value=True)
