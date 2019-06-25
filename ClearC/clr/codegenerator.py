"""
Module for generating code from an annotated ast.
"""

from typing import List, Tuple, Dict

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
        # Locals are just left on the stack and params/upvalues aren't declared

    def op(self, opcode: bc.Instruction) -> None:
        self.code.append(opcode)

    def start_function(self) -> int:
        self.code.append(bc.Opcode.FUNCTION)
        self.code.append(0)
        return len(self.code) - 1

    def end_function(self, size_index: int) -> None:
        size = bc.size(self.code[size_index + 1 :])
        self.code[size_index] = size

    def emit_return(self, function: ast.AstFuncDecl) -> None:
        for _ in range(1 + len(function.block.names)):
            self.code.append(bc.Opcode.POP)
        self.code.append(bc.Opcode.LOAD_FP)
        self.code.append(bc.Opcode.LOAD_IP)

    def make_struct(self, size: int) -> None:
        self.code.append(bc.Opcode.STRUCT)
        self.code.append(size)

    def get_upvalue(self, index: int) -> None:
        # Load the function struct
        self.code.append(bc.Opcode.PUSH_LOCAL)
        self.code.append(0)
        # If it's not the recursion upvalue get it from the struct
        if index != 0:
            self.code.append(bc.Opcode.GET_FIELD)
            self.code.append(index)

    def load(self, index_annot: an.IndexAnnot) -> None:
        if index_annot.kind == an.IndexAnnotType.GLOBAL:
            self.code.append(bc.Opcode.PUSH_GLOBAL)
            self.code.append(index_annot.value)
        elif index_annot.kind == an.IndexAnnotType.UPVALUE:
            self.get_upvalue(index_annot.value)
            self.code.append(bc.Opcode.DEREF)
        else:
            self.code.append(bc.Opcode.PUSH_LOCAL)
            self.code.append(index_annot.value)

    def upvalue(self, index_annot: an.IndexAnnot) -> None:
        if index_annot.kind == an.IndexAnnotType.UPVALUE:
            self.get_upvalue(index_annot.value)
        else:
            self.code.append(bc.Opcode.REF_LOCAL)
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


class CodeGenerator(ast.FunctionVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.program = Program()

    def value_decl(self, node: ast.AstValueDecl) -> None:
        super().value_decl(node)
        self.program.declare(node.index_annot)

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        function = self.program.start_function()
        super().func_decl(node)
        if node.return_type.type_annot == an.BuiltinTypeAnnot.VOID:
            self.program.emit_return(node)
        self.program.end_function(function)
        for ref in node.upvalue_refs:
            self.program.upvalue(ref)
        self.program.make_struct(len(node.upvalue_refs) + 1)
        self.program.declare(node.index_annot)

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        super().print_stmt(node)
        if node.expr:
            not_string = node.expr.type_annot != an.BuiltinTypeAnnot.STR
            self.program.print_value(convert=not_string)
        else:
            self.program.constant("")
            self.program.print_value(convert=False)

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        super().block_stmt(node)
        for _ in node.names:
            self.program.op(bc.Opcode.POP)

    def return_stmt(self, node: ast.AstReturnStmt) -> None:
        super().return_stmt(node)
        if node.expr:
            self.program.op(bc.Opcode.SET_RETURN)
        self.program.emit_return(self._functions[-1])

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        super().expr_stmt(node)
        self.program.op(bc.Opcode.POP)

    def unary_expr(self, node: ast.AstUnaryExpr) -> None:
        super().unary_expr(node)
        unary_ops: Dict[str, Dict[an.TypeAnnot, bc.Opcode]] = {
            "-": {
                an.BuiltinTypeAnnot.NUM: bc.Opcode.NUM_NEG,
                an.BuiltinTypeAnnot.INT: bc.Opcode.INT_NEG,
            }
        }
        operator = str(node.operator)
        self.program.op(unary_ops[operator][node.target.type_annot])

    def binary_expr(self, node: ast.AstBinaryExpr) -> None:
        super().binary_expr(node)
        typed_binary_ops: Dict[str, Dict[an.TypeAnnot, bc.Opcode]] = {
            "+": {
                an.BuiltinTypeAnnot.NUM: bc.Opcode.NUM_ADD,
                an.BuiltinTypeAnnot.INT: bc.Opcode.INT_ADD,
                an.BuiltinTypeAnnot.STR: bc.Opcode.STR_CAT,
            },
            "-": {
                an.BuiltinTypeAnnot.NUM: bc.Opcode.NUM_SUB,
                an.BuiltinTypeAnnot.INT: bc.Opcode.INT_SUB,
            },
            "*": {
                an.BuiltinTypeAnnot.NUM: bc.Opcode.NUM_MUL,
                an.BuiltinTypeAnnot.INT: bc.Opcode.INT_MUL,
            },
            "/": {
                an.BuiltinTypeAnnot.NUM: bc.Opcode.NUM_DIV,
                an.BuiltinTypeAnnot.INT: bc.Opcode.INT_DIV,
            },
        }
        untyped_binary_ops = {
            "==": [bc.Opcode.EQUAL],
            "!=": [bc.Opcode.EQUAL, bc.Opcode.NOT],
        }
        operator = str(node.operator)
        if operator in typed_binary_ops:
            self.program.op(typed_binary_ops[operator][node.left.type_annot])
        else:
            for opcode in untyped_binary_ops[operator]:
                self.program.op(opcode)

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

    def bool_expr(self, node: ast.AstBoolExpr) -> None:
        super().bool_expr(node)
        self.program.op(bc.Opcode.PUSH_TRUE if node.value else bc.Opcode.PUSH_FALSE)

    def nil_expr(self, node: ast.AstNilExpr) -> None:
        super().nil_expr(node)
        self.program.op(bc.Opcode.PUSH_NIL)

    def call_expr(self, node: ast.AstCallExpr) -> None:
        # TODO: Built-in functions
        super().call_expr(node)
        # Get the ip
        self.program.op(bc.Opcode.EXTRACT_FIELD)
        self.program.op(len(node.args))
        self.program.op(0)
        # Make the new frame
        self.program.op(bc.Opcode.CALL)
        self.program.op(len(node.args) + 1)
        # Fetch the return value if there is one
        if isinstance(node.function.type_annot, an.FuncTypeAnnot):  # should be true
            if node.function.type_annot.return_type != an.BuiltinTypeAnnot.VOID:
                self.program.op(bc.Opcode.PUSH_RETURN)
