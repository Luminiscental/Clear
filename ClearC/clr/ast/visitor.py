class ExprVisitor:
    def visit_call_expr(self, node):
        node.target.accept(self)
        for arg in node.arguments:
            arg.accept(self)

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

    def visit_ident_expr(self, node):
        pass

    def visit_string_expr(self, node):
        pass

    def visit_number_expr(self, node):
        pass

    def visit_boolean_expr(self, node):
        pass


class StmtVisitor(ExprVisitor):
    def start_scope(self):
        pass

    def end_scope(self):
        pass

    def visit_block_stmt(self, node):
        self.start_scope()
        for decl in node.declarations:
            if not decl.is_stmt:
                continue
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
        node.value.accept(self)


class DeclVisitor(StmtVisitor):
    def visit_block_stmt(self, node):
        # Override the stmt version of this to also accept the declarations
        self.start_scope()
        for decl in node.declarations:
            decl.accept(self)
        self.end_scope()

    def visit_func_decl(self, node):
        node.block.accept(self)

    def visit_val_decl(self, node):
        node.value.accept(self)