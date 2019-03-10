from clr.errors import emit_error
from clr.assemble import assembled_size
from clr.constants import Constants, ClrUint
from clr.values import OpCode, DEBUG
from clr.tokens import TokenType, token_info


class Program:
    def __init__(self):
        self.code_list = []

    def load_constant(self, constant):
        self.code_list.append(OpCode.LOAD_CONST)
        self.code_list.append(constant)

    def simple_op(self, opcode):
        self.code_list.append(opcode)

    def push_scope(self):
        self.simple_op(OpCode.PUSH_SCOPE)

    def pop_scope(self):
        self.simple_op(OpCode.POP_SCOPE)

    def define_name(self, resolved_name):
        if resolved_name.is_global:
            self.code_list.append(OpCode.DEFINE_GLOBAL)
        else:
            self.code_list.append(OpCode.DEFINE_LOCAL)
        self.code_list.append(resolved_name.index)

    def load_name(self, resolved_name):
        self.code_list.append(
            OpCode.LOAD_GLOBAL if resolved_name.is_global else OpCode.LOAD_LOCAL
        )
        self.code_list.append(resolved_name.index)

    def begin_jump(self, conditional=False, leave_value=False):
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
        index, conditional = jump_ref
        contained = self.code_list[index + 1 :]
        offset = assembled_size(contained)
        if DEBUG:
            print(f"Jump from {index} set with offset {offset}")
        self.code_list[index] = ClrUint(offset)
        if conditional and not leave_value:
            self.code_list.append(OpCode.POP)

    def flush(self):
        return self.code_list


class Compiler:
    def __init__(self):
        self.program = Program()
        self.constants = Constants()

    def flush_code(self):
        return self.constants.flush() + self.program.flush()

    def init_value(self, resolved_name, initializer):
        initializer.gen_code(self)
        self.program.define_name(resolved_name)

    def print_expression(self, expression):
        if expression is None:
            self.program.simple_op(OpCode.PRINT_BLANK)
        else:
            expression.gen_code(self)
            self.program.simple_op(OpCode.PRINT)

    def run_if(self, checks, otherwise):
        final_jumps = []
        for check in checks:
            check_cond, check_block = check
            check_cond.gen_code(self)
            check_jump = self.program.begin_jump(conditional=True)
            check_block.gen_code(self)
            final_jumps.append(self.program.begin_jump())
            self.program.end_jump(check_jump)
        if otherwise is not None:
            otherwise.gen_code(self)
        for final_jump in final_jumps:
            self.program.end_jump(final_jump)

    def drop_expression(self, expression):
        expression.gen_code(self)
        self.program.simple_op(OpCode.POP)

    def push_scope(self):
        self.program.push_scope()

    def pop_scope(self):
        self.program.pop_scope()

    def apply_unary(self, operator, expression):
        expression.gen_code(self)
        {
            TokenType.MINUS: lambda: self.program.simple_op(OpCode.NEGATE),
            TokenType.BANG: lambda: self.program.simple_op(OpCode.NOT),
        }.get(
            operator.token_type,
            emit_error(f"Unknown unary operator! {token_info(operator)}"),
        )()

    def apply_binary(self, operator, left_expr, right_expr):
        left_expr.gen_code(self)
        right_expr.gen_code(self)
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
            operator.token_type,
            emit_error(f"Unknown binary operator! {token_info(operator)}"),
        )()

    def load_constant(self, value):
        const_index = self.constants.add(value)
        self.program.load_constant(const_index)

    def load_boolean(self, token):
        {
            TokenType.TRUE: lambda: self.program.simple_op(OpCode.TRUE),
            TokenType.FALSE: lambda: self.program.simple_op(OpCode.FALSE),
        }.get(
            token.token_type, emit_error(f"Expected boolean token! {token_info(token)}")
        )()

    def load_variable(self, resolved_name):
        self.program.load_name(resolved_name)

    def apply_builtin(self, builtin, target):
        target.gen_code(self)
        {
            TokenType.TYPE: lambda: self.program.simple_op(OpCode.TYPE),
            TokenType.INT: lambda: self.program.simple_op(OpCode.INT),
            TokenType.BOOL: lambda: self.program.simple_op(OpCode.BOOL),
            TokenType.NUM: lambda: self.program.simple_op(OpCode.NUM),
            TokenType.STR: lambda: self.program.simple_op(OpCode.STR),
        }.get(
            builtin.token_type,
            emit_error(f"Expected built-in function! {token_info(builtin)}"),
        )()

    def apply_and(self, left_expr, right_expr):
        left_expr.gen_code(self)
        short_circuit = self.program.begin_jump(conditional=True)
        right_expr.gen_code(self)
        self.program.end_jump(short_circuit, leave_value=True)

    def apply_or(self, left_expr, right_expr):
        left_expr.gen_code(self)
        long_circuit = self.program.begin_jump(conditional=True, leave_value=True)
        short_circuit = self.program.begin_jump()
        self.program.end_jump(long_circuit)
        right_expr.gen_code(self)
        self.program.end_jump(short_circuit, leave_value=True)
