from collections import defaultdict
from clr.errors import emit_error
from clr.values import OpCode, DEBUG
from clr.assemble import assembled_size
from clr.tokens import TokenType, token_info
from clr.constants import ClrUint, Constants
from clr.ast.index_annotations import IndexAnnotationType, INDEX_OF_THIS
from clr.ast.type_annotations import (
    BUILTINS,
    VOID_TYPE,
    STR_TYPE,
    INT_TYPE,
    NUM_TYPE,
    BOOL_TYPE,
)
from clr.ast.visitor import DeclVisitor
from clr.ast.expression_nodes import IdentExpr


class Program:
    def __init__(self):
        self.code_list = []
        self.scopes = [0]

    def load_constant(self, index):
        self.code_list.append(OpCode.PUSH_CONST)
        self.code_list.append(index)

    def push_scope(self):
        self.scopes.append(0)

    def pop_scope(self):
        for _ in range(self.scopes.pop()):
            self.simple_op(OpCode.POP)

    def simple_op(self, opcode):
        self.code_list.append(opcode)

    def define_name(self, index):
        def add_local():
            self.scopes[-1] += 1

        {
            IndexAnnotationType.GLOBAL: lambda: self.code_list.extend(
                [OpCode.SET_GLOBAL, index.value]
            ),
            IndexAnnotationType.LOCAL: add_local,
            IndexAnnotationType.UPVALUE: emit_error("Closures unimplemented"),
        }.get(
            index.kind, emit_error(f"Cannot define name with index kind {index.kind}!")
        )()

    def set_name(self, index):
        opcode = {
            IndexAnnotationType.GLOBAL: lambda: OpCode.SET_GLOBAL,
            IndexAnnotationType.LOCAL: lambda: OpCode.SET_LOCAL,
            IndexAnnotationType.UPVALUE: emit_error("Closures unimplemented"),
        }.get(
            index.kind, emit_error(f"Cannot set name with index kind {index.kind}!")
        )()
        self.code_list.append(opcode)
        self.code_list.append(index.value)

    def load_name(self, index):
        opcode = {
            IndexAnnotationType.GLOBAL: lambda: OpCode.PUSH_GLOBAL,
            IndexAnnotationType.LOCAL: lambda: OpCode.PUSH_LOCAL,
            IndexAnnotationType.PARAM: emit_error("Functions unimplemented"),
            IndexAnnotationType.UPVALUE: emit_error("Closures unimplemented"),
        }.get(index.kind, emit_error(f"Cannot load unresolved name of {index}!"))()
        self.code_list.append(opcode)
        self.code_list.append(index.value)

    def begin_function(self):
        emit_error("Functions unimplemented")()
        self.code_list.append(OpCode.START_FUNCTION)
        index = len(self.code_list)
        # Insert temporary offset to later be patched
        self.code_list.append(ClrUint(0))
        return index

    def end_function(self, index):
        emit_error("Functions unimplemented")()
        contained = self.code_list[index + 1 :]
        offset = assembled_size(contained)
        # Patch the previously inserted offset
        self.code_list[index] = ClrUint(offset)

    def make_closure(self, upvalues=None):
        emit_error("Closures unimplemented")()
        upvalues = upvalues or []
        self.code_list.append(OpCode.CLOSURE)
        self.code_list.append(len(upvalues))
        for upvalue in upvalues:
            if DEBUG:
                print(f"Loading upvalue {upvalue}")
            self.load_name(upvalue)

    def begin_jump(self, conditional=False):
        emit_error("Control flow unimplemented")()
        self.code_list.append(OpCode.JUMP_IF_NOT if conditional else OpCode.JUMP)
        index = len(self.code_list)
        if DEBUG:
            print(f"Defining a jump from {index}")
        # Insert temporary offset to later be patched
        temp_offset = ClrUint(0)
        self.code_list.append(temp_offset)
        return index

    def end_jump(self, jump_ref):
        emit_error("Control flow unimplemented")()
        index = jump_ref
        contained = self.code_list[index + 1 :]
        offset = assembled_size(contained)
        if DEBUG:
            print(f"Jump from {index} set with offset {offset}")
        # Patch the previously inserted offset
        self.code_list[index] = ClrUint(offset)

    def begin_loop(self):
        emit_error("Control flow unimplemented")()
        index = len(self.code_list)
        if DEBUG:
            print(f"Loop checkpoint for {index} picked")
        return index

    def loop_back(self, index):
        emit_error("Control flow unimplemented")()
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

    def _end_expression(self, node):
        if node.polymorphed_fields is not None:
            emit_error("Structs unimplemented")()
            self.program.simple_op(OpCode.GET_FIELDS)
            self.program.simple_op(len(node.polymorphed_fields))
            for field in node.polymorphed_fields:
                self.program.simple_op(field)
            self.program.simple_op(OpCode.STRUCT)
            self.program.simple_op(len(node.polymorphed_fields))

    def _make_function(self, node):
        emit_error("Functions unimplemented")()
        function = self.program.begin_function()
        for decl in node.block.declarations:
            decl.accept(self)
        if node.return_type.as_annotation == VOID_TYPE:
            self.program.simple_op(OpCode.RETURN_VOID)
        self.program.end_function(function)

    def visit_func_decl(self, node):
        emit_error("Functions unimplemented")()
        # No super as we handle scoping
        self._make_function(node)
        # Store the function object as a local to close over
        self.program.define_name(node.index_annotation)
        # Load the decorator if it exists
        if node.decorator:
            node.decorator.accept(self)
        # Close the function
        self.program.load_name(node.index_annotation)
        self.program.make_closure(node.upvalues)
        # Decorate the function
        if node.decorator:
            self.program.simple_op(OpCode.CALL)
            self.program.simple_op(1)
        # Define the function as the final value
        self.program.define_name(node.index_annotation)

    def visit_prop_decl(self, node):
        emit_error("Properties unimplemented")()

    def visit_struct_decl(self, node):
        emit_error("Structs unimplemented")()
        # No super as we handle methods
        # Make all method function objects
        for method in node.methods.values():
            self._make_function(method)
            self.program.define_name(method.index_annotation)
            if method.decorator:
                method.decorator.accept(self)
                self.program.define_name(method.decorator_index_annotation)
        # Create the constructor
        function = self.program.begin_function()
        field_count = len(node.fields)
        # Load all the fields, reversed so that they are in order on the stack
        param_index = len([i for i in range(field_count) if i not in node.methods]) - 1
        for i in reversed(range(field_count)):
            if i in node.methods:
                # If it's a method temporarily put a dummy value until the struct is created
                self.program.simple_op(OpCode.FALSE)
            else:
                # If it's a field load its parameter
                self.program.simple_op(OpCode.LOAD_PARAM)
                self.program.simple_op(param_index)
                param_index -= 1
        # Create the struct value from the fields
        self.program.simple_op(OpCode.STRUCT)
        self.program.simple_op(field_count)
        # Store the result as the instance local
        self.program.define_name(INDEX_OF_THIS)
        # Patch in and close all the methods
        for i in reversed(range(field_count)):
            if i in node.methods:
                method = node.methods[i]
                # Load the instance for the later SET_FIELD op
                self.program.load_name(INDEX_OF_THIS)
                # Load the decorator to call if it exists
                if method.decorator:
                    self.program.load_name(
                        method.decorator_constructor_index_annotation
                    )
                # Load the method
                self.program.load_name(method.constructor_index_annotation)
                # Close it
                self.program.make_closure(method.upvalues)
                # Decorate it
                if method.decorator:
                    self.program.simple_op(OpCode.CALL)
                    self.program.simple_op(1)
                # Put it in the field
                self.program.simple_op(OpCode.SET_FIELD)
                self.program.simple_op(i)
        # Load the struct to return
        self.program.load_name(INDEX_OF_THIS)
        self.program.simple_op(OpCode.RETURN)
        self.program.end_function(function)
        self.program.make_closure(node.upvalues)
        # Define the constructor as this function value
        self.program.define_name(node.index_annotation)

    def visit_print_stmt(self, node):
        super().visit_print_stmt(node)
        if node.value is None:
            self.program.load_constant(self.constants.add(""))
        elif node.value.type_annotation != STR_TYPE:
            self.program.simple_op(OpCode.STR)
        self.program.simple_op(OpCode.PRINT)

    def visit_if_stmt(self, node):
        emit_error("Control flow unimplemented")()
        # No super because we need the jumps in the right place
        # Create a list of jumps that skip to the end once a block completes
        final_jumps = []
        for cond, block in node.checks:
            cond.accept(self)
            # If the condition is false jump to the next block
            jump = self.program.begin_jump(conditional=True)
            # Otherwise pop the condition as we don't need it
            self.program.simple_op(OpCode.POP)
            # And run the block
            block.accept(self)
            # Then jump to the end after the block completes
            final_jumps.append(self.program.begin_jump())
            # The jump to the next block goes after the jump to the end to avoid it
            self.program.end_jump(jump)
            # Also pop the condition if the block was skipped
            self.program.simple_op(OpCode.POP)
        if node.otherwise is not None:
            # If we haven't jumped to the end then all the previous blocks didn't execute so run the
            # else block
            node.otherwise.accept(self)
        for final_jump in final_jumps:
            # All the final jumps end here after everything
            self.program.end_jump(final_jump)

    def visit_while_stmt(self, node):
        emit_error("Control flow unimplemented")()
        # No super because the loop starts before checking the condition
        loop = self.program.begin_loop()
        if node.condition is not None:
            node.condition.accept(self)
            # If there is a condition jump to the end if it's false
            skip_jump = self.program.begin_jump(conditional=True)
            # Otherwise pop the condition as we don't need it
            self.program.simple_op(OpCode.POP)
        node.block.accept(self)
        # Go back to before the condition to check it again
        self.program.loop_back(loop)
        if node.condition is not None:
            self.program.end_jump(skip_jump)
            # If we broke out the condition is still there so pop it
            self.program.simple_op(OpCode.POP)

    def visit_ret_stmt(self, node):
        emit_error("Functions unimplemented")()
        super().visit_ret_stmt(node)
        if node.value is None:
            self.program.simple_op(OpCode.RETURN_VOID)
        else:
            self.program.simple_op(OpCode.RETURN)

    def visit_expr_stmt(self, node):
        super().visit_expr_stmt(node)
        if node.value.type_annotation != VOID_TYPE:
            self.program.simple_op(OpCode.POP)

    def start_scope(self):
        super().start_scope()
        self.program.push_scope()

    def end_scope(self):
        super().end_scope()
        self.program.pop_scope()

    def visit_unary_expr(self, node):
        super().visit_unary_expr(node)
        self.program.simple_op(
            {
                TokenType.MINUS: lambda: {
                    INT_TYPE: OpCode.INT_NEG,
                    NUM_TYPE: OpCode.NUM_NEG,
                },
                TokenType.BANG: lambda: {BOOL_TYPE: OpCode.NOT},
            }.get(
                node.operator.token_type,
                emit_error(f"Unknown unary operator! {token_info(node.operator)}"),
            )()[
                node.type_annotation
            ]
        )
        self._end_expression(node)

    def visit_assign_expr(self, node):
        # Don't call super as we don't want to evaluate the left hand side
        node.right.accept(self)
        self.program.set_name(node.left.index_annotation)
        if DEBUG:
            print(f"Loading name for {node.left}")
        # Assignment is an expression so we load the assigned value as well
        self.program.load_name(node.left.index_annotation)
        self._end_expression(node)

    def visit_access_expr(self, node):
        emit_error("Structs unimplemented")()
        super().visit_access_expr(node)
        self.program.simple_op(OpCode.GET_FIELD)
        self.program.simple_op(node.right.index_annotation.value)
        self._end_expression(node)

    def visit_binary_expr(self, node):
        super().visit_binary_expr(node)
        binary_codes = {
            TokenType.PLUS: {
                INT_TYPE: [OpCode.INT_ADD],
                NUM_TYPE: [OpCode.NUM_ADD],
                STR_TYPE: [OpCode.STR_CAT],
            },
            TokenType.MINUS: {INT_TYPE: [OpCode.INT_SUB], NUM_TYPE: [OpCode.NUM_SUB]},
            TokenType.STAR: {INT_TYPE: [OpCode.INT_MUL], NUM_TYPE: [OpCode.NUM_MUL]},
            TokenType.SLASH: {INT_TYPE: [OpCode.INT_DIV], NUM_TYPE: [OpCode.NUM_DIV]},
            TokenType.EQUAL_EQUAL: defaultdict(lambda: [OpCode.EQUAL]),
            TokenType.BANG_EQUAL: defaultdict(lambda: [OpCode.EQUAL, OpCode.NOT]),
            TokenType.LESS: {INT_TYPE: [OpCode.INT_LESS], NUM_TYPE: [OpCode.NUM_LESS]},
            TokenType.GREATER_EQUAL: {
                INT_TYPE: [OpCode.INT_LESS, OpCode.NOT],
                NUM_TYPE: [OpCode.NUM_LESS, OpCode.NOT],
            },
            TokenType.GREATER: {
                INT_TYPE: [OpCode.INT_GREATER],
                NUM_TYPE: [OpCode.NUM_GREATER, OpCode.NOT],
            },
            TokenType.LESS_EQUAL: {INT_TYPE: [OpCode.INT_GREATER, OpCode.NOT]},
        }
        if node.operator.token_type not in binary_codes:
            emit_error(f"Unknown binary operator! {token_info(node.operator)}")()
        for code in binary_codes[node.operator.token_type][node.left.type_annotation]:
            self.program.simple_op(code)
        self._end_expression(node)

    def visit_unpack_expr(self, node):
        emit_error("Control flow unimplemented")()
        # No super as we need the jumps in the right place
        # Load the target value
        node.target.accept(self)
        # Compare check if it isn't nil
        self.program.simple_op(OpCode.NIL)
        self.program.simple_op(OpCode.NEQUAL)

        def load_present_value():
            # Create the present value function
            implicit_function = self.program.begin_function()
            # Evaluate the present-value
            node.present_value.accept(self)
            # Return from the evaluating function
            if node.present_value.type_annotation != VOID_TYPE:
                self.program.simple_op(OpCode.RETURN)
            else:
                self.program.simple_op(OpCode.RETURN_VOID)
            self.program.end_function(implicit_function)
            self.program.make_closure(node.upvalues)
            # Call the function with the target value as a single argument
            node.target.accept(self)
            self.program.simple_op(OpCode.CALL)
            self.program.simple_op(1)

        # Both cases present `a? b : c` - if a is present evaluates to b otherwise c
        if node.present_value is not None and node.default_value is not None:
            # If the target isn't present skip the present-case
            jump_past_present = self.program.begin_jump(conditional=True)
            # Otherwise pop the condition and load the present-case
            self.program.simple_op(OpCode.POP)
            load_present_value()
            # Then skip past the default-case
            jump_to_end = self.program.begin_jump()
            self.program.end_jump(jump_past_present)
            # If the present-case was skipped pop the condition and load the default-case
            self.program.simple_op(OpCode.POP)
            node.default_value.accept(self)
            self.program.end_jump(jump_to_end)
        # Present-case only `a? b` - b is a void expression that is only evaluated if a is present
        elif node.present_value is not None:
            # If the target isn't present skip the present-case
            skip = self.program.begin_jump(conditional=True)
            # Otherwise load the present-case
            load_present_value()
            # If it's a discarded expression pop it as the unpack counts as void after
            if node.present_value.type_annotation != VOID_TYPE:
                self.program.simple_op(OpCode.POP)
            self.program.end_jump(skip)
            # Pop the condition
            self.program.simple_op(OpCode.POP)
        # Default-case only: `a?: b` - if a is present evaluates to a if non-void, otherwise b
        elif node.default_value is not None:
            # If the target isn't present skip the present-case
            jump_past_present = self.program.begin_jump(conditional=True)
            # Otherwise pop the condition
            self.program.simple_op(OpCode.POP)
            if node.default_value.type_annotation != VOID_TYPE:
                # Load the target in the present-case if it's a non-void expression
                node.target.accept(self)
            # Then skip past the default-case
            jump_to_end = self.program.begin_jump()
            self.program.end_jump(jump_past_present)
            # If the present-case was skipped pop the condition and load the default-case
            self.program.simple_op(OpCode.POP)
            node.default_value.accept(self)
            self.program.end_jump(jump_to_end)
        self._end_expression(node)

    def visit_lambda_expr(self, node):
        emit_error("Functions unimplemented")()
        # No super as we handle params / scoping
        function = self.program.begin_function()
        node.result.accept(self)
        return_op = (
            OpCode.RETURN_VOID
            if node.type_annotation.return_type == VOID_TYPE
            else OpCode.RETURN
        )
        self.program.simple_op(return_op)
        self.program.end_function(function)
        self.program.make_closure(node.upvalues)
        self._end_expression(node)

    def visit_if_expr(self, node):
        emit_error("Control flow unimplemented")()
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
        # If we haven't jumped to the end then all the previous blocks didn't execute so run the
        # else block
        node.otherwise.accept(self)
        for final_jump in final_jumps:
            # All the final jumps end here after everything
            self.program.end_jump(final_jump)
        self._end_expression(node)

    def visit_call_expr(self, node):
        if isinstance(node.target, IdentExpr) and node.target.name.lexeme in BUILTINS:
            # Don't call super if it's a built-in because we don't want to evaluate the name
            opcode = BUILTINS[node.target.name.lexeme].opcode
            for arg in node.arguments:
                arg.accept(self)
            self.program.simple_op(opcode)
        else:
            emit_error("Functions unimplemented")()
            super().visit_call_expr(node)
            self.program.simple_op(OpCode.CALL)
            self.program.simple_op(len(node.arguments))
        self._end_expression(node)

    def visit_construct_expr(self, node):
        emit_error("Structs unimplemented")()
        # Load the constructor before calling super() as callable comes before arguments
        self.program.load_name(node.constructor_index_annotation)
        super().visit_construct_expr(node)
        # Call the constructor
        self.program.simple_op(OpCode.CALL)
        self.program.simple_op(len(node.args))
        self._end_expression(node)

    def _visit_constant_expr(self, node):
        const_index = self.constants.add(node.value)
        self.program.load_constant(const_index)
        self._end_expression(node)

    def visit_number_expr(self, node):
        super().visit_number_expr(node)
        self._visit_constant_expr(node)
        self._end_expression(node)

    def visit_string_expr(self, node):
        super().visit_string_expr(node)
        self._visit_constant_expr(node)
        self._end_expression(node)

    def visit_boolean_expr(self, node):
        super().visit_boolean_expr(node)
        self.program.simple_op(OpCode.PUSH_TRUE if node.value else OpCode.PUSH_FALSE)
        self._end_expression(node)

    def visit_keyword_expr(self, node):
        super().visit_keyword_expr(node)
        if node.token.token_type == TokenType.THIS:
            emit_error("Structs unimplemented")()
            self.program.load_name(node.index_annotation)
        elif node.token.token_type == TokenType.NIL:
            self.program.simple_op(OpCode.PUSH_NIL)
        self._end_expression(node)

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        if DEBUG:
            print(f"Loading name for {node}")
        self.program.load_name(node.index_annotation)
        self._end_expression(node)

    def visit_and_expr(self, node):
        emit_error("Control flow unimplemented")()
        # No super because we need to put the jumps in the right place
        node.left.accept(self)
        # If the first value is false don't bother checking the second
        short_circuit = self.program.begin_jump(conditional=True)
        # Otherwise pop the false value and load the second
        self.program.simple_op(OpCode.POP)
        node.right.accept(self)
        self.program.end_jump(short_circuit)
        self._end_expression(node)

    def visit_or_expr(self, node):
        emit_error("Control flow unimplemented")()
        # No super because we need to put the jumps in the right place
        node.left.accept(self)
        # If the first value is false jump past the shortcircuit
        long_circuit = self.program.begin_jump(conditional=True)
        # If we haven't skipped the shortcircuit jump to the end
        short_circuit = self.program.begin_jump()
        # If we skipped the shortcircuit pop the first value to replace with the second one
        self.program.end_jump(long_circuit)
        self.program.simple_op(OpCode.POP)
        node.right.accept(self)
        # If we short circuited leave the true value on the stack
        self.program.end_jump(short_circuit)
        self._end_expression(node)
