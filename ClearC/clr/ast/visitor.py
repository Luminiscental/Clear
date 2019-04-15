from clr.ast.statement_nodes import StmtNode


class TypeVisitor:
    def visit_void_type(self, node):
        pass

    def visit_simple_type(self, node):
        pass

    def visit_func_type(self, node):
        for param in node.params:
            param.accept(self)
        node.return_type.accept(self)


class ExprVisitor(TypeVisitor):
    def visit_call_expr(self, node):
        node.target.accept(self)
        for arg in node.arguments:
            arg.accept(self)

    def visit_construct_expr(self, node):
        for _, field_value in node.args.items():
            field_value.accept(self)

    def visit_assign_expr(self, node):
        node.left.accept(self)
        node.right.accept(self)

    def visit_access_expr(self, node):
        node.left.accept(self)

    def visit_unary_expr(self, node):
        node.target.accept(self)

    def visit_binary_expr(self, node):
        node.left.accept(self)
        node.right.accept(self)

    def visit_and_expr(self, node):
        node.left.accept(self)
        node.right.accept(self)

    def visit_or_expr(self, node):
        node.left.accept(self)
        node.right.accept(self)

    def visit_this_expr(self, node):
        pass

    def visit_ident_expr(self, node):
        pass

    def visit_string_expr(self, node):
        pass

    def visit_number_expr(self, node):
        pass

    def visit_boolean_expr(self, node):
        pass


class StmtVisitor(ExprVisitor):
    def __init__(self):
        self.errors = []

    def start_scope(self):
        pass

    def end_scope(self):
        pass

    def visit_block_stmt(self, node):
        self.start_scope()
        for decl in node.declarations:
            if isinstance(decl, StmtNode):
                decl.accept(self)
        self.end_scope()

    def visit_expr_stmt(self, node):
        node.value.accept(self)

    def visit_ret_stmt(self, node):
        node.value.accept(self)

    def visit_while_stmt(self, node):
        if node.condition is not None:
            node.condition.accept(self)
        node.block.accept(self)

    def visit_if_stmt(self, node):
        for cond, block in node.checks:
            cond.accept(self)
            block.accept(self)
        if node.otherwise is not None:
            node.otherwise.accept(self)

    def visit_print_stmt(self, node):
        if node.value:
            node.value.accept(self)


class DeclVisitor(StmtVisitor):
    def visit_block_stmt(self, node):
        # Override the stmt version of this to also accept the declarations
        self.start_scope()
        for decl in node.declarations:
            decl.accept(self)
        self.end_scope()

    def visit_val_decl(self, node):
        node.initializer.accept(self)

    def visit_func_decl(self, node):
        for param_type, _ in node.params:
            param_type.accept(self)
        node.return_type.accept(self)
        node.block.accept(self)

    def visit_method_decl(self, node):
        self.visit_func_decl(node)

    def visit_struct_decl(self, node):
        for field_type, _ in node.fields:
            field_type.accept(self)
        for method in node.methods.values():
            self.visit_method_decl(method)


class StructTrackingDeclVisitor(DeclVisitor):
    def __init__(self):
        super().__init__()
        self.structs = {}

    def visit_struct_decl(self, node):
        self.structs[node.name.lexeme] = node
        super().visit_struct_decl(node)
