"""
Module for generating code from an annotated ast.
"""

from typing import List, Tuple

import clr.ast as ast
import clr.annotations as an
import clr.bytecode as bc


def generate_code(tree: ast.Ast) -> Tuple[List[bc.Constant], List[bc.Instruction]]:
    generator = CodeGenerator()
    tree.accept(generator)
    return generator.program.constants, generator.program.code


class Program:
    def __init__(self) -> None:
        self.code: List[bc.Instruction] = []
        self.constants: List[bc.Constant] = []

    def declare(self, index_annot: an.IndexAnnot) -> None:
        if index_annot.kind == an.IndexAnnotType.GLOBAL:
            self.code.append(bc.Opcode.SET_GLOBAL)
            self.code.append(index_annot.value)
        # Locals are just left on the stack and params/upvalues can't be set

    def start_function(self) -> int:
        self.code.append(bc.Opcode.FUNCTION)
        self.code.append(0)
        return len(self.code) - 1

    def end_function(self, size_index: int) -> None:
        size = bc.size(self.code[size_index + 1 :])
        self.code[size_index] = size

    def make_struct(self, size: int) -> None:
        self.code.append(bc.Opcode.STRUCT)
        self.code.append(size)

    def load(self, index_annot: an.IndexAnnot) -> None:
        if index_annot.kind == an.IndexAnnotType.GLOBAL:
            self.code.append(bc.Opcode.PUSH_GLOBAL)
            self.code.append(index_annot.value)
        elif index_annot.kind == an.IndexAnnotType.UPVALUE:
            # Load the function struct
            self.code.append(bc.Opcode.PUSH_LOCAL)
            self.code.append(0)
            # If it's not the recursion upvalue get it from the struct
            if index_annot.value != 0:
                # Get the upvalue from the struct
                self.code.append(bc.Opcode.GET_FIELD)
                self.code.append(index_annot.value)
        else:
            self.code.append(bc.Opcode.PUSH_LOCAL)
            self.code.append(index_annot.value)

    def constant(self, value: bc.Constant) -> None:
        if value in self.constants:
            index = self.constants.index(value)
        else:
            index = len(self.constants)
            self.constants.append(value)
        self.code.append(bc.Opcode.PUSH_CONST)
        self.code.append(index)

    def print_value(self, convert: bool) -> None:
        if convert:
            self.code.append(bc.Opcode.STR)
        self.code.append(bc.Opcode.PRINT)


class CodeGenerator(ast.DeepVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.program = Program()

    def value_decl(self, node: ast.AstValueDecl) -> None:
        super().value_decl(node)
        self.program.declare(node.index_annot)

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        function = self.program.start_function()
        super().func_decl(node)
        self.program.end_function(function)
        for ref in node.upvalue_refs:
            self.program.load(ref)
        self.program.make_struct(len(node.upvalue_refs) + 1)

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        super().print_stmt(node)
        if node.expr:
            not_string = node.expr.type_annot != an.BuiltinTypeAnnot.STR
            self.program.print_value(convert=not_string)
        else:
            self.program.constant("")
            self.program.print_value(convert=False)

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
        self.program.load(node.index_annot)
