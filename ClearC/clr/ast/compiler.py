from clr.errors import emit_error
from clr.values import OpCode, DEBUG
from clr.assemble import assembled_size
from clr.tokens import TokenType, token_info
from clr.constants import ClrUint, Constants
from clr.ast.index_annotations import IndexAnnotation, IndexAnnotationType
from clr.ast.type_annotations import BUILTINS, VOID_TYPE
from clr.ast.visitor import DeclVisitor
from clr.ast.expression_nodes import IdentExpr


class Program:
    def __init__(self):
        self.code_list = []

    def load_constant(self, index):
        self.code_list.append(OpCode.LOAD_CONST)
        self.code_list.append(index)

    def simple_op(self, opcode):
        self.code_list.append(opcode)

    def define_name(self, index):
        opcode = {
            IndexAnnotationType.GLOBAL: lambda: OpCode.DEFINE_GLOBAL,
            IndexAnnotationType.LOCAL: lambda: OpCode.DEFINE_LOCAL,
            IndexAnnotationType.UPVALUE: lambda: OpCode.SET_UPVALUE,
        }.get(
            index.kind, emit_error(f"Cannot define name with index kind {index.kind}!")
        )()
        self.code_list.append(opcode)
        self.code_list.append(index.value)

    def load_name(self, index):
        opcode = {
            IndexAnnotationType.GLOBAL: lambda: OpCode.LOAD_GLOBAL,
            IndexAnnotationType.LOCAL: lambda: OpCode.LOAD_LOCAL,
            IndexAnnotationType.PARAM: lambda: OpCode.LOAD_PARAM,
            IndexAnnotationType.UPVALUE: lambda: OpCode.LOAD_UPVALUE,
        }.get(index.kind, emit_error(f"Cannot load unresolved name of {index}!"))()
        self.code_list.append(opcode)
        self.code_list.append(index.value)

    def begin_function(self):
        self.code_list.append(OpCode.START_FUNCTION)
        index = len(self.code_list)
        # Insert temporary offset to later be patched
        self.code_list.append(ClrUint(0))
        return index

    def end_function(self, index):
        contained = self.code_list[index + 1 :]
        offset = assembled_size(contained)
        # Patch the previously inserted offset
        self.code_list[index] = ClrUint(offset)

    def make_closure(self, upvalues=None):
        upvalues = upvalues or []
        self.code_list.append(OpCode.CLOSURE)
        self.code_list.append(len(upvalues))
        for upvalue in upvalues:
            if DEBUG:
                print(f"Loading upvalue {upvalue}")
            self.load_name(upvalue)

    def begin_jump(self, conditional=False, leave_value=False):
        self.code_list.append(OpCode.JUMP_IF_NOT if conditional else OpCode.JUMP)
        index = len(self.code_list)
        if DEBUG:
            print(f"Defining a jump from {index}")
        # Insert temporary offset to later be patched
        temp_offset = ClrUint(0)
        self.code_list.append(temp_offset)
        # If there was a condition and we aren't told to leave it pop it from the stack
        if conditional and not leave_value:
            self.code_list.append(OpCode.POP)
        return index, conditional

    def end_jump(self, jump_ref, leave_value=False):
        index, conditional = jump_ref
        contained = self.code_list[index + 1 :]
        offset = assembled_size(contained)
        if DEBUG:
            print(f"Jump from {index} set with offset {offset}")
        # Patch the previously inserted offset
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
        # Insert an offset temporarily to include it when calculating the actual offset.
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
        super().__init__()
        self.program = Program()
        self.constants = Constants()

    def flush_code(self):
        return self.constants.flush() + self.program.flush()

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        self.program.define_name(node.index_annotation)

    def _make_function(self, node):
        function = self.program.begin_function()
        for decl in node.block.declarations:
            decl.accept(self)
        if node.return_type.as_annotation == VOID_TYPE:
            self.program.simple_op(OpCode.RETURN_VOID)
        self.program.end_function(function)

    def visit_func_decl(self, node):
        # No super as we handle scoping
        self._make_function(node)
        self.program.make_closure(node.upvalues)
        # Define the function as the closure value
        self.program.define_name(node.index_annotation)

    def visit_struct_decl(self, node):
        # No super as we handle methods
        # Make all method function objects
        for method in node.methods.values():
            self._make_function(method)
            self.program.define_name(method.index_annotation)
        # Create the constructor
        function = self.program.begin_function()
        field_count = len(node.fields)
        # Load all the fields
        param_index = 0
        # Reversed so that they are in order on the stack
        for i in reversed(range(field_count)):
            if i in node.methods:
                # If it's a method load the method and close it
                method = node.methods[i]
                # There is a different index for referencing it from within the constructor
                self.program.load_name(method.constructor_index_annotation)
                self.program.make_closure()
            else:
                # If it's a field load its parameter
                self.program.simple_op(OpCode.LOAD_PARAM)
                self.program.simple_op(param_index)
                param_index += 1
        # Create the struct value from the fields
        self.program.simple_op(OpCode.STRUCT)
        self.program.simple_op(field_count)
        # Return the struct value
        self.program.simple_op(OpCode.RETURN)
        self.program.end_function(function)
        self.program.make_closure(node.upvalues)
        # Define the constructor as this function value
        self.program.define_name(node.index_annotation)

    def visit_print_stmt(self, node):
        super().visit_print_stmt(node)
        if node.value is None:
            self.program.simple_op(OpCode.PRINT_BLANK)
        else:
            self.program.simple_op(OpCode.PRINT)

    def visit_if_stmt(self, node):
        # No super because we need the jumps in the right place
        # Create a list of jumps that skip to the end once a block completes
        final_jumps = []
        for cond, block in node.checks:
            cond.accept(self)
            # If the condition is false jump to the next block
            jump = self.program.begin_jump(conditional=True)
            block.accept(self)
            # Otherwise jump to the end after the block completes
            final_jumps.append(self.program.begin_jump())
            # The jump to the next block goes after the jump to the end to avoid it
            self.program.end_jump(jump)
        if node.otherwise is not None:
            # If we haven't jumped to the end then all the previous blocks didn't execute so run the
            # else block
            node.otherwise.accept(self)
        for final_jump in final_jumps:
            # All the final jumps end here after everything
            self.program.end_jump(final_jump)

    def visit_while_stmt(self, node):
        # No super because the loop starts before checking the condition
        loop = self.program.begin_loop()
        if node.condition is not None:
            node.condition.accept(self)
            # If there is a condition jump to the end if it's false
            skip_jump = self.program.begin_jump(conditional=True)
        node.block.accept(self)
        # Go back to before the condition to check it again
        self.program.loop_back(loop)
        if node.condition is not None:
            self.program.end_jump(skip_jump)

    def visit_ret_stmt(self, node):
        super().visit_ret_stmt(node)
        self.program.simple_op(OpCode.RETURN)

    def visit_expr_stmt(self, node):
        super().visit_expr_stmt(node)
        if node.value.type_annotation != VOID_TYPE:
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
            self.program.define_name(node.left.index_annotation)
            if DEBUG:
                print(f"Loading name for {node.left}")
            # Assignment is an expression so we load the assigned value as well
            self.program.load_name(node.left.index_annotation)
        elif node.operator.token_type == TokenType.DOT:
            node.left.accept(self)
            self.program.simple_op(OpCode.GET_FIELD)
            self.program.simple_op(node.right.index_annotation.value)
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
        if isinstance(node.target, IdentExpr) and node.target.name.lexeme in BUILTINS:
            # Don't call super if it's a built-in because we don't want to evaluate the name
            opcode = BUILTINS[node.target.name.lexeme].opcode
            for arg in node.arguments:
                arg.accept(self)
            self.program.simple_op(opcode)
        else:
            super().visit_call_expr(node)
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
        if DEBUG:
            print(f"Loading name for {node}")
        self.program.load_name(node.index_annotation)

    def visit_and_expr(self, node):
        # No super because we need to put the jumps in the right place
        node.left.accept(self)
        short_circuit = self.program.begin_jump(conditional=True)
        # If the first is false jump past the second, if we don't jump pop the value to replace
        # with the second one
        node.right.accept(self)
        # If we jumped here because the first was false leave that false value on the stack
        self.program.end_jump(short_circuit, leave_value=True)

    def visit_or_expr(self, node):
        # No super because we need to put the jumps in the right place
        node.left.accept(self)
        # If the first value is false jump past the shortcircuit
        long_circuit = self.program.begin_jump(conditional=True, leave_value=True)
        # If we haven't skipped the shortcircuit jump to the end
        short_circuit = self.program.begin_jump()
        # If we skipped the shortcircuit pop the first value to replace with the second one
        self.program.end_jump(long_circuit)
        node.right.accept(self)
        # If we short circuited leave the true value on the stack
        self.program.end_jump(short_circuit, leave_value=True)
