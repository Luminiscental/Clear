from clr.assemble import assembled_size
from clr.constants import Constants, ClrUint
from clr.values import OpCode, DEBUG
from clr.ast.visitor import DeclVisitor
from clr.ast.index import Index
from clr.tokens import TokenType, token_info
from clr.errors import emit_error
from clr.ast.resolve import BUILTINS


class Program:
    def __init__(self):
        self.code_list = []

    def load_constant(self, constant):
        self.code_list.append(OpCode.LOAD_CONST)
        self.code_list.append(constant)

    def simple_op(self, opcode):
        self.code_list.append(opcode)

    def define_name(self, index):
        if index.kind == Index.GLOBAL:
            self.code_list.append(OpCode.DEFINE_GLOBAL)
        else:
            self.code_list.append(OpCode.DEFINE_LOCAL)
        self.code_list.append(index.value)

    def set_name(self, index):
        if index.kind == Index.GLOBAL:
            self.code_list.append(OpCode.DEFINE_GLOBAL)
        else:
            self.code_list.append(OpCode.DEFINE_LOCAL)
        self.code_list.append(index.value)

    def load_name(self, index):
        opcode = None
        if index.kind == Index.GLOBAL:
            opcode = OpCode.LOAD_GLOBAL
        elif index.kind == Index.PARAM:
            opcode = OpCode.LOAD_PARAM
        elif index.kind == Index.LOCAL:
            opcode = OpCode.LOAD_LOCAL
        else:
            emit_error(f"Could not load unresolved name {index}!")()
        self.code_list.append(opcode)
        self.code_list.append(index.value)

    def begin_function(self):
        self.code_list.append(OpCode.START_FUNCTION)
        index = len(self.code_list)
        self.code_list.append(ClrUint(0))
        return index

    def end_function(self, index):
        contained = self.code_list[index + 1 :]
        offset = assembled_size(contained)
        self.code_list[index] = ClrUint(offset)

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

    def begin_loop(self):
        index = len(self.code_list)
        if DEBUG:
            print(f"Loop checkpoint for {index} picked")
        return index

    def loop_back(self, index):
        self.code_list.append(OpCode.LOOP)
        offset_index = len(self.code_list)
        self.code_list.append(ClrUint(0))
        contained = self.code_list[index:]
        offset = ClrUint(assembled_size(contained))
        if DEBUG:
            print(f"Loop back to {index} set with offset {offset}")
        self.code_list[offset_index] = offset

    def flush(self):
        return self.code_list


class Compiler(DeclVisitor):
    def __init__(self):
        self.program = Program()
        self.constants = Constants()

    def flush_code(self):
        return self.constants.flush() + self.program.flush()

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        self.program.define_name(node.index_annotation)

    def visit_func_decl(self, node):
        # No super as we handle scoping
        function = self.program.begin_function()
        for decl in node.block.declarations:
            decl.accept(self)
        self.program.end_function(function)
        self.program.define_name(node.index_annotation)

    def visit_print_stmt(self, node):
        super().visit_print_stmt(node)
        if node.value is None:
            self.program.simple_op(OpCode.PRINT_BLANK)
        else:
            self.program.simple_op(OpCode.PRINT)

    def visit_if_stmt(self, node):
        # No super because we need the jumps in the right place
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

    def visit_while_stmt(self, node):
        # No super because the loop starts before checking the condition
        loop = self.program.begin_loop()
        if node.condition is not None:
            node.condition.accept(self)
            skip_jump = self.program.begin_jump(conditional=True)
        node.block.accept(self)
        self.program.loop_back(loop)
        if node.condition is not None:
            self.program.end_jump(skip_jump)

    def visit_ret_stmt(self, node):
        super().visit_ret_stmt(node)
        self.program.simple_op(OpCode.RETURN)

    def visit_expr_stmt(self, node):
        super().visit_expr_stmt(node)
        self.program.simple_op(OpCode.POP)

    def start_scope(self):
        super().start_scope()
        self.program.simple_op(OpCode.PUSH_SCOPE)

    def end_scope(self):
        super().end_scope()
        self.program.simple_op(OpCode.POP_SCOPE)

    def visit_unary_expr(self, node):
        super().visit_unary_expr(node)
        {
            TokenType.MINUS: lambda: self.program.simple_op(OpCode.NEGATE),
            TokenType.BANG: lambda: self.program.simple_op(OpCode.NOT),
        }.get(
            node.operator.token_type,
            emit_error(f"Unknown unary operator! {token_info(node.operator)}"),
        )()

    def visit_binary_expr(self, node):
        if node.operator.token_type == TokenType.EQUAL:
            # If it's an assignment don't call super as we don't want to evaluate the left hand side
            node.right.accept(self)
            self.program.set_name(node.left.index_annotation)
            if DEBUG:
                print(f"Loading name for {node.left.get_info()}")
            self.program.load_name(node.left.index_annotation)
        else:
            super().visit_binary_expr(node)
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

    def visit_call_expr(self, node):
        super().visit_call_expr(node)
        if node.target.name.lexeme in BUILTINS:
            _, opcode = BUILTINS[node.target.name.lexeme]
            self.program.simple_op(opcode)
        else:
            self.program.simple_op(OpCode.CALL)
            self.program.simple_op(len(node.arguments))

    def _visit_constant_expr(self, node):
        const_index = self.constants.add(node.value)
        self.program.load_constant(const_index)

    def visit_number_expr(self, node):
        super().visit_number_expr(node)
        self._visit_constant_expr(node)

    def visit_string_expr(self, node):
        super().visit_string_expr(node)
        self._visit_constant_expr(node)

    def visit_boolean_expr(self, node):
        super().visit_boolean_expr(node)
        self.program.simple_op(OpCode.TRUE if node.value else OpCode.FALSE)

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        if node.name.lexeme not in BUILTINS:
            if DEBUG:
                print(f"Loading name for {node.get_info()}")
            self.program.load_name(node.index_annotation)

    def visit_and_expr(self, node):
        # No super because we need to put the jumps in the right place
        node.left.accept(self)
        short_circuit = self.program.begin_jump(conditional=True)
        node.right.accept(self)
        self.program.end_jump(short_circuit, leave_value=True)

    def visit_or_expr(self, node):
        # No super because we need to put the jumps in the right place
        node.left.accept(self)
        long_circuit = self.program.begin_jump(conditional=True, leave_value=True)
        short_circuit = self.program.begin_jump()
        self.program.end_jump(long_circuit)
        node.right.accept(self)
        self.program.end_jump(short_circuit, leave_value=True)
