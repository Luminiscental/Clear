"""
Module for generating code from an annotated ast.
"""

from typing import List, Tuple, Optional, Iterator

import contextlib

import clr.ast as ast
import clr.annotations as an
import clr.bytecode as bc


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

    def start_function(self) -> int:
        """
        Start a function, returns an index that is used by end_function.
        """
        self.code.append(bc.Opcode.FUNCTION)
        self.code.append(0)
        return len(self.code) - 1

    def end_function(self, size_index: int) -> None:
        """
        End a function, patches the size argument using the passed index.
        """
        size = bc.size(self.code[size_index + 1 :])
        self.code[size_index] = size

    @contextlib.contextmanager
    def condition(self, condition: bool) -> Iterator[None]:
        """
        Context manager for conditional execution.
        """
        jump = self.begin_jump(not condition)
        yield
        self.end_jump(jump)

    def begin_jump(self, condition: Optional[bool] = None) -> int:
        """
        Emit a jump instruction, possibly checking for a boolean condition. Returns an index used
        by end_jump.
        """
        if condition is None:
            self.code.append(bc.Opcode.JUMP)
        else:
            if condition:
                self.code.append(bc.Opcode.NOT)
            self.code.append(bc.Opcode.JUMP_IF_FALSE)
        index = len(self.code)
        self.code.append(0)
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
        self.code.append(bc.Opcode.LOOP)
        index = len(self.code)
        self.code.append(0)
        size = bc.size(self.code[target + 1 :])
        self.code[index] = size

    def emit_return(self, function: ast.AstFuncDecl) -> None:
        """
        Returns from the function call.
        """
        # TODO: POPN
        for _ in range(1 + len(function.block.names)):
            self.code.append(bc.Opcode.POP)
        self.code.append(bc.Opcode.LOAD_FP)
        self.code.append(bc.Opcode.LOAD_IP)

    def get_upvalue(self, index: int) -> None:
        """
        Get an upvalue from the function.
        """
        # Load the function struct
        self.code.append(bc.Opcode.PUSH_LOCAL)
        self.code.append(0)
        # If it's not the recursion upvalue get it from the struct
        if index != 0:
            self.code.append(bc.Opcode.GET_FIELD)
            self.code.append(index)

    def load(self, index_annot: an.IndexAnnot) -> None:
        """
        Load a value given its index.
        """
        if index_annot.kind == an.IndexAnnotType.GLOBAL:
            self.code.append(bc.Opcode.PUSH_GLOBAL)
            self.code.append(index_annot.value)
        elif index_annot.kind == an.IndexAnnotType.UPVALUE:
            self.get_upvalue(index_annot.value)
            if index_annot.value != 0:
                self.code.append(bc.Opcode.DEREF)
        else:
            self.code.append(bc.Opcode.PUSH_LOCAL)
            self.code.append(index_annot.value)

    def upvalue(self, index_annot: an.IndexAnnot) -> None:
        """
        Make an upvalue to an index.
        """
        if index_annot.kind == an.IndexAnnotType.UPVALUE:
            self.get_upvalue(index_annot.value)
        else:
            self.code.append(bc.Opcode.REF_LOCAL)
            self.code.append(index_annot.value)

    def constant(self, value: bc.Constant) -> None:
        """
        Load a constant value.
        """
        if value in self.constants:
            index = self.constants.index(value)
        else:
            index = len(self.constants)
            self.constants.append(value)
        self.code.append(bc.Opcode.PUSH_CONST)
        self.code.append(index)

    def print_value(self, convert: bool) -> None:
        """
        Print a temporary value, possibly converting to a string first.
        """
        if convert:
            self.code.append(bc.Opcode.STR)
        self.code.append(bc.Opcode.PRINT)


class CodeGenerator(ast.FunctionVisitor):
    """
    Ast visitor to build up a program from the annotated ast.
    """

    def __init__(self) -> None:
        super().__init__()
        self.program = Program()

    def value_decl(self, node: ast.AstValueDecl) -> None:
        super().value_decl(node)
        self.program.declare(node.index_annot)

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        function = self.program.start_function()
        super().func_decl(node)
        if node.return_type.type_annot == an.VOID:
            self.program.emit_return(node)
        self.program.end_function(function)
        for ref in node.upvalue_refs:
            self.program.upvalue(ref)
        self.program.append_op(bc.Opcode.STRUCT)
        self.program.append_op(len(node.upvalue_refs) + 1)
        self.program.declare(node.index_annot)

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        super().print_stmt(node)
        if node.expr:
            not_string = node.expr.type_annot != an.STR
            self.program.print_value(convert=not_string)
        else:
            self.program.constant("")
            self.program.print_value(convert=False)

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        super().block_stmt(node)
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
        super().return_stmt(node)
        if node.expr:
            self.program.append_op(bc.Opcode.SET_RETURN)
        self.program.emit_return(self._functions[-1])

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        super().expr_stmt(node)
        if node.expr.type_annot != an.VOID:
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
        super().int_expr(node)
        self.program.constant(node.value)

    def num_expr(self, node: ast.AstNumExpr) -> None:
        super().num_expr(node)
        self.program.constant(node.value)

    def str_expr(self, node: ast.AstStrExpr) -> None:
        super().str_expr(node)
        self.program.constant(node.value)

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        super().ident_expr(node)
        # TODO: Make print a builtin not a statement
        # TODO: Cache the function if it's used multiple times
        # TODO: Elide the function if it gets called straight away
        if node.name in an.BUILTINS:
            builtin = an.BUILTINS[node.name]
            if isinstance(builtin.type_annot, an.FuncTypeAnnot):
                function = self.program.start_function()
                for i in range(len(builtin.type_annot.params)):
                    self.program.append_op(bc.Opcode.PUSH_LOCAL)
                    self.program.append_op(1 + i)
                self.program.append_op(an.BUILTINS[node.name].opcode)
                if builtin.type_annot.return_type != an.VOID:
                    self.program.append_op(bc.Opcode.SET_RETURN)
                for _ in builtin.type_annot.params:
                    self.program.append_op(bc.Opcode.POP)
                self.program.append_op(bc.Opcode.POP)
                self.program.append_op(bc.Opcode.LOAD_FP)
                self.program.append_op(bc.Opcode.LOAD_IP)
                self.program.end_function(function)
                self.program.append_op(bc.Opcode.STRUCT)
                self.program.append_op(1)
        else:
            self.program.load(node.index_annot)

    def bool_expr(self, node: ast.AstBoolExpr) -> None:
        super().bool_expr(node)
        self.program.append_op(
            bc.Opcode.PUSH_TRUE if node.value else bc.Opcode.PUSH_FALSE
        )

    def nil_expr(self, node: ast.AstNilExpr) -> None:
        super().nil_expr(node)
        self.program.append_op(bc.Opcode.PUSH_NIL)

    def call_expr(self, node: ast.AstCallExpr) -> None:
        super().call_expr(node)
        # Get the ip
        self.program.append_op(bc.Opcode.EXTRACT_FIELD)
        self.program.append_op(len(node.args))
        self.program.append_op(0)
        # Make the new frame
        self.program.append_op(bc.Opcode.CALL)
        self.program.append_op(len(node.args) + 1)
        # Fetch the return value if there is one
        if isinstance(node.function.type_annot, an.FuncTypeAnnot):  # should be true
            if node.function.type_annot.return_type != an.VOID:
                self.program.append_op(bc.Opcode.PUSH_RETURN)
