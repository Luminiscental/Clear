"""
Module for generating code from an annotated ast.
"""

from typing import List, Tuple, Optional, Iterator, Dict

import contextlib

import clr.ast as ast
import clr.annotations as an
import clr.types as ts
import clr.bytecode as bc
import clr.util as util


def generate_code(tree: ast.Ast) -> Tuple[List[bc.Constant], List[bc.Instruction]]:
    """
    Produce a list of instructions and constants from an annotated ast.
    """
    generator = CodeGenerator()
    tree.accept(generator)
    return generator.program.constants, generator.program.code


class Program:
    """
    Class wrapping a program with instructions and constants.
    """

    def __init__(self) -> None:
        self.code: List[bc.Instruction] = []
        self.constants: List[bc.Constant] = []
        self.type_tags: List[ts.Type] = []

    def declare(self, index_annot: an.IndexAnnot) -> None:
        """
        Take a temporary value and declare it as the given index.
        """
        if index_annot.kind == an.IndexAnnotType.GLOBAL:
            self.code.append(bc.Opcode.SET_GLOBAL)
            self.code.append(index_annot.value)
        # Locals are just left on the stack and params/upvalues aren't declared

    def append_op(self, opcode: bc.Instruction) -> None:
        """
        Append an instruction.
        """
        self.code.append(opcode)

    def match_type(self, index_annot: an.IndexAnnot, type_annot: ts.Type) -> None:
        """
        Checks if the given value is of the given type.
        """
        value_types: Dict[ts.UnitType, bc.ValueType] = {
            ts.BuiltinType.BOOL: bc.ValueType.BOOL,
            ts.BuiltinType.NIL: bc.ValueType.NIL,
            ts.BuiltinType.INT: bc.ValueType.INT,
            ts.BuiltinType.NUM: bc.ValueType.NUM,
        }

        self.load(index_annot)
        end_jumps = []

        def end_true() -> None:
            # Pop the target value
            self.append_op(bc.Opcode.POP)
            # Push the result
            self.append_op(bc.Opcode.PUSH_TRUE)
            # Jump to the end
            end_jumps.append(self.begin_jump())

        # Check against all the subtypes
        for subtype in type_annot.units:
            if subtype in value_types:
                # If it's a value type just use IS_VAL_TYPE
                self.append_op(bc.Opcode.IS_VAL_TYPE)
                self.append_op(value_types[subtype].value)
                with self.condition(True):
                    end_true()
            else:
                # Otherwise make sure it's an object
                self.append_op(bc.Opcode.IS_VAL_TYPE)
                self.append_op(bc.ValueType.OBJ.value)
                with self.condition(True):
                    if subtype == ts.STR:
                        # Check for strings with IS_OBJ_TYPE
                        self.append_op(bc.Opcode.IS_OBJ_TYPE)
                        self.append_op(bc.ObjectType.STRING.value)
                        with self.condition(True):
                            end_true()
                    if isinstance(subtype, (ts.FunctionType, ts.TupleType)):
                        # Other types are type tagged structs, make sure it's a struct
                        self.append_op(bc.Opcode.IS_OBJ_TYPE)
                        self.append_op(bc.ObjectType.STRUCT.value)
                        with self.condition(True):
                            # Check against all the type tags that are contained in the match
                            for i, tag in enumerate(self.type_tags):
                                if subtype in tag.units:
                                    # Get the tag from the struct
                                    self.append_op(bc.Opcode.EXTRACT_FIELD)
                                    self.append_op(0)
                                    self.append_op(0)
                                    # Compare it
                                    self.constant(bc.ClrInt(i))
                                    self.append_op(bc.Opcode.EQUAL)
                                    with self.condition(True):
                                        end_true()
        # If we didn't jump to the end then none of the type checks matched and the result is false
        # Pop the target value
        self.append_op(bc.Opcode.POP)
        # Push the result
        self.append_op(bc.Opcode.PUSH_FALSE)
        # End the jumps for true results after the false result
        for jump in end_jumps:
            self.end_jump(jump)

    @contextlib.contextmanager
    def function(
        self, type_annot: ts.Type, upvalues: List[an.IndexAnnot]
    ) -> Iterator[None]:
        """
        Context manager for creating a type tagged function with upvalues.
        """
        # Make the function struct, which stores the ip and any upvalues
        # Tagged with the function type
        with self.struct(type_annot, field_count=1 + len(upvalues)):
            self.append_op(bc.Opcode.FUNCTION)
            idx = len(self.code)
            # Put a temporary function size argument to be patched after
            self.append_op(0)
            yield
            # Patch the actual function size
            size = bc.size(self.code[idx + 1 :])
            self.code[idx] = size
            # Load the upvalues to go into the struct above the ip from OP_FUNCTION
            for ref in upvalues:
                self.upvalue(ref)

    @contextlib.contextmanager
    def struct(self, type_annot: ts.Type, field_count: int) -> Iterator[None]:
        """
        Context manager for creating a type tagged struct.
        """
        # Make the type tag index
        if type_annot in self.type_tags:
            self.constant(bc.ClrInt(self.type_tags.index(type_annot)))
        else:
            self.constant(bc.ClrInt(len(self.type_tags)))
            self.type_tags.append(type_annot)
        yield
        # Make the struct with the given number of fields plus the type tag
        self.append_op(bc.Opcode.STRUCT)
        self.append_op(field_count + 1)

    @contextlib.contextmanager
    def condition(self, condition: bool) -> Iterator[None]:
        """
        Context manager for conditional execution. Pops a boolean value off the stack and only
        executes the contained code if the value is equal to the passed condition.
        """
        # Begin a jump to skip if the condition isn't met
        jump = self.begin_jump(not condition)
        yield
        # End after the skipping jump after the content
        self.end_jump(jump)

    def begin_jump(self, condition: Optional[bool] = None) -> int:
        """
        Emit a jump instruction, possibly checking for a boolean condition. Returns an index used
        by end_jump.
        """
        if condition is None:
            self.append_op(bc.Opcode.JUMP)
        else:
            if condition:
                self.append_op(bc.Opcode.NOT)
            self.append_op(bc.Opcode.JUMP_IF_FALSE)
        index = len(self.code)
        self.append_op(0)
        return index

    def end_jump(self, index: int) -> None:
        """
        Given an index patches the offset of the jump at that index.
        """
        size = bc.size(self.code[index + 1 :])
        self.code[index] = size

    def start_loop(self) -> int:
        """
        Begins a loop, returning an index used by loop_back.
        """
        return len(self.code) - 1

    def loop_back(self, target: int) -> None:
        """
        Given a target index loops back to the instrucion at that index.
        """
        self.append_op(bc.Opcode.LOOP)
        index = len(self.code)
        self.append_op(0)
        size = bc.size(self.code[target + 1 :])
        self.code[index] = size

    def emit_return(self) -> None:
        """
        Returns from the function call.
        """
        # Pop the function struct
        self.append_op(bc.Opcode.POP)
        # Load the previous frame pointer
        self.append_op(bc.Opcode.LOAD_FP)
        # Load the previous instruction pointer
        self.append_op(bc.Opcode.LOAD_IP)

    def get_upvalue(self, index: int) -> None:
        """
        Get an upvalue from the function.
        """
        # Load the function struct
        self.append_op(bc.Opcode.PUSH_LOCAL)
        self.append_op(0)
        # If it's not the recursion upvalue get it from the struct
        if index != 0:
            self.append_op(bc.Opcode.GET_FIELD)
            self.append_op(1 + index)

    def load(self, index_annot: an.IndexAnnot) -> None:
        """
        Load a value given its index.
        """
        if index_annot.kind == an.IndexAnnotType.GLOBAL:
            self.append_op(bc.Opcode.PUSH_GLOBAL)
            self.append_op(index_annot.value)
        elif index_annot.kind == an.IndexAnnotType.UPVALUE:
            self.get_upvalue(index_annot.value)
            # If it's not the function struct deref it
            if index_annot.value != 0:
                self.append_op(bc.Opcode.DEREF)
        else:
            self.append_op(bc.Opcode.PUSH_LOCAL)
            self.append_op(index_annot.value)

    def upvalue(self, index_annot: an.IndexAnnot) -> None:
        """
        Make an upvalue to an index.
        """
        if index_annot.kind == an.IndexAnnotType.UPVALUE:
            self.get_upvalue(index_annot.value)
        else:
            # Assume that it isn't a global, since globals aren't ever upvalues
            self.append_op(bc.Opcode.REF_LOCAL)
            self.append_op(index_annot.value)

    def constant(self, value: bc.Constant) -> None:
        """
        Load a constant value.
        """
        if value in self.constants:
            index = self.constants.index(value)
        else:
            index = len(self.constants)
            self.constants.append(value)
        self.append_op(bc.Opcode.PUSH_CONST)
        self.append_op(index)


class CodeGenerator(ast.FunctionVisitor):
    """
    Ast visitor to build up a program from the annotated ast.
    """

    def __init__(self) -> None:
        super().__init__()
        self.program = Program()

    def _return(self, node: ast.AstFuncDecl) -> None:
        # If the function block is in scope pop all the names in it
        if node.block in self._scopes:
            function_scopes = util.break_after(node.block, reversed(self._scopes))
            for scope in function_scopes:
                for _ in scope.names:
                    self.program.append_op(bc.Opcode.POP)
        # Emit the return
        self.program.emit_return()

    def value_decl(self, node: ast.AstValueDecl) -> None:
        node.val_init.accept(self)
        if len(node.bindings) == 1:
            self.program.declare(node.bindings[0].index_annot)
        else:
            self.program.append_op(bc.Opcode.DESTRUCT)
            # Skip the type tag
            self.program.append_op(1)
            # Declare all the bindings
            for binding in reversed(node.bindings):
                self.program.declare(binding.index_annot)

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        with self.program.function(node.type_annot, node.upvalue_indices):
            super().func_decl(node)
            if node.return_type.type_annot == ts.VOID:
                self._return(node)
        self.program.declare(node.index_annot)

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        if node.expr:
            node.expr.accept(self)
            if node.expr.type_annot != ts.STR:
                self.program.append_op(bc.Opcode.STR)
        else:
            # Blank print statements print an empty string
            self.program.constant(bc.ClrStr(""))
        self.program.append_op(bc.Opcode.PRINT)

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        super().block_stmt(node)
        # Pop all the locals
        for _ in node.names:
            self.program.append_op(bc.Opcode.POP)
        # Reset so they don't get popped again
        node.names.clear()

    def if_stmt(self, node: ast.AstIfStmt) -> None:
        end_jumps = []
        conds = [node.if_part] + node.elif_parts
        # Go through all the conditions
        for cond, block in conds:
            cond.accept(self)
            with self.program.condition(True):
                # If the condition is true execute the block and jump to the end
                block.accept(self)
                end_jumps.append(self.program.begin_jump())
        # If we haven't jumped to the end and there's an else block execute it
        if node.else_part:
            node.else_part.accept(self)
        # End after the if, elif, and else parts
        for jump in end_jumps:
            self.program.end_jump(jump)

    def while_stmt(self, node: ast.AstWhileStmt) -> None:
        loop = self.program.start_loop()

        def run() -> None:
            # Running the loop means executing the block and looping back
            node.block.accept(self)
            self.program.loop_back(loop)

        if node.cond:
            # If there is a condition, check it and only run if it's true
            node.cond.accept(self)
            with self.program.condition(True):
                run()
        else:
            # Otherwise run unconditionally
            run()

    def return_stmt(self, node: ast.AstReturnStmt) -> None:
        if node.expr:
            node.expr.accept(self)
            self.program.append_op(bc.Opcode.SET_RETURN)
        # Shouldn't be in a lambda since it's a statement
        function = self._get_function()
        if isinstance(function, ast.AstFuncDecl):
            self._return(function)

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        node.expr.accept(self)
        if node.expr.type_annot != ts.VOID:
            self.program.append_op(bc.Opcode.POP)

    def unary_expr(self, node: ast.AstUnaryExpr) -> None:
        super().unary_expr(node)
        for opcode in node.opcodes:
            self.program.append_op(opcode)

    def binary_expr(self, node: ast.AstBinaryExpr) -> None:
        super().binary_expr(node)
        for opcode in node.opcodes:
            self.program.append_op(opcode)

    def int_expr(self, node: ast.AstIntExpr) -> None:
        self.program.constant(bc.ClrInt(node.value))

    def num_expr(self, node: ast.AstNumExpr) -> None:
        self.program.constant(bc.ClrNum(node.value))

    def str_expr(self, node: ast.AstStrExpr) -> None:
        self.program.constant(bc.ClrStr(node.value))

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        # TODO: Make print a builtin not a statement
        # TODO: Cache the function if it's used multiple times
        # TODO: Elide the function if it gets called straight away
        if node.name in ts.BUILTINS:
            builtin = ts.BUILTINS[node.name]
            as_func = builtin.type_annot.get_function()
            if as_func is not None:  # Should be true
                with self.program.function(builtin.type_annot, upvalues=[]):
                    # Load all the parameters
                    for i in range(len(as_func.parameters)):
                        self.program.append_op(bc.Opcode.PUSH_LOCAL)
                        self.program.append_op(1 + i)
                    # Call the builtin
                    self.program.append_op(builtin.opcode)
                    # Return
                    if as_func.return_type != ts.VOID:
                        self.program.append_op(bc.Opcode.SET_RETURN)
                    for _ in as_func.parameters:
                        self.program.append_op(bc.Opcode.POP)
                    self.program.emit_return()
        else:
            self.program.load(node.index_annot)

    def bool_expr(self, node: ast.AstBoolExpr) -> None:
        self.program.append_op(
            bc.Opcode.PUSH_TRUE if node.value else bc.Opcode.PUSH_FALSE
        )

    def nil_expr(self, node: ast.AstNilExpr) -> None:
        self.program.append_op(bc.Opcode.PUSH_NIL)

    def case_expr(self, node: ast.AstCaseExpr) -> None:
        node.target.accept(self)
        end_jumps = []

        def use_value(value: ast.AstExpr) -> None:
            # Load the value
            value.accept(self)
            # Replace the target with it
            self.program.append_op(
                bc.Opcode.SQUASH if node.type_annot != ts.VOID else bc.Opcode.POP
            )
            # Go to the end
            end_jumps.append(self.program.begin_jump())

        for case_type, case_value in node.cases:
            # Check if the type matches
            self.program.match_type(node.binding.index_annot, case_type.type_annot)
            with self.program.condition(True):
                # If it does use it as the result
                use_value(case_value)
        # If we haven't jumped to the end there should be a fallback
        if node.fallback:
            use_value(node.fallback)
        for jump in end_jumps:
            self.program.end_jump(jump)

    def call_expr(self, node: ast.AstCallExpr) -> None:
        # Load the function and arguments
        super().call_expr(node)
        # Extract the ip from the function beneath the arguments
        self.program.append_op(bc.Opcode.EXTRACT_FIELD)
        self.program.append_op(len(node.args))
        # ip is the first element, but offset by the type tag
        self.program.append_op(1 + 0)
        # Call the function
        self.program.append_op(bc.Opcode.CALL)
        self.program.append_op(len(node.args) + 1)
        # Fetch the return value if there is one
        as_func = node.function.type_annot.get_function()
        if as_func is not None:  # Should be true
            if as_func.return_type != ts.VOID:
                self.program.append_op(bc.Opcode.PUSH_RETURN)

    def tuple_expr(self, node: ast.AstTupleExpr) -> None:
        # Make a struct from all the elements
        with self.program.struct(node.type_annot, field_count=len(node.exprs)):
            super().tuple_expr(node)

    def lambda_expr(self, node: ast.AstLambdaExpr) -> None:
        with self.program.function(node.type_annot, node.upvalue_indices):
            # Load the value
            node.value.accept(self)
            # Return the value
            if node.value.type_annot != ts.VOID:
                self.program.append_op(bc.Opcode.SET_RETURN)
            # The only locals to pop are the params
            for _ in node.params:
                self.program.append_op(bc.Opcode.POP)
            self.program.emit_return()
