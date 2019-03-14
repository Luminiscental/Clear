"""
This module provides classes to inherent to implement behaviour for visiting an AST tree or
accepting visitors as part of an AST tree.
"""


class AstVisitable:
    """
    This class specifies a default no-op function for accepting a visitor.
    """

    def accept(self, visitor):
        """
        This function accepts a visitor, and by default does nothing
        """


class AstVisitor:
    """
    This class specifies functions for visiting an AST tree.
    """

    def visit_val_decl(self, node):
        """
        This function is called when visiting a value declaration, and by default does nothing, iterating onto the child.
        """
        node.value.accept(self)

    def visit_func_decl(self, node):
        """
        This function is called when visiting a function declaration, and by default does nothing,
        iterating onto the child.
        """
        node.block.accept(self)

    def visit_print_stmt(self, node):
        """
        This function is called when visiting a print statement, and by default does nothing, iterating onto a child if it exists.
        """
        if node.value:
            node.value.accept(self)

    def visit_if_stmt(self, node):
        """
        This function is called when visiting an if statement, and by default does nothing, iterating onto the children.
        """
        for cond, block in node.checks:
            cond.accept(self)
            block.accept(self)
        if node.otherwise is not None:
            node.otherwise.accept(self)

    def visit_while_stmt(self, node):
        """
        This function is called when visiting an if statement, and by default does nothing, iterating onto the children.
        """
        if node.condition is not None:
            node.condition.accept(self)
        node.block.accept(self)

    def visit_ret_stmt(self, node):
        """
        This function is called when visiting a return statement, and by default does nothing, iterating onto the child.
        """
        node.value.accept(self)

    def visit_expr_stmt(self, node):
        """
        This function is called when visiting an expression statement, and by default does nothing, iterating onto the child.
        """
        node.value.accept(self)

    def start_block_stmt(self, node):
        """
        This function is called before visiting the contents of a block, and by default does
        nothing.
        """

    def end_block_stmt(self, node):
        """
        This function is called after visiting the contents of a block, and by default does
        nothing.
        """

    def visit_decl(self, node):
        """
        This function is called after visiting a declaration root, and by default does nothing, iterating onto the child.
        """
        node.value.accept(self)

    def visit_stmt(self, node):
        """
        This function is called after visiting a statement root, and by default does nothing, iterating onto the child.
        """
        node.value.accept(self)

    def visit_expr(self, node):
        """
        This function is called after visiting an expression root, and by default does nothing, iterating onto the child.
        """
        node.value.accept(self)

    def visit_unary_expr(self, node):
        """
        This function is called when visiting a unary expression, and by default does nothing, iterating onto the child.
        """
        node.target.accept(self)

    def visit_binary_expr(self, node):
        """
        This function is called when visiting a binary expression, and by default does nothing, iterating onto the children.
        """
        node.left.accept(self)
        node.right.accept(self)

    def visit_call_expr(self, node):
        """
        This function is called when visiting a call expression, and by default does nothing, iterating onto the children.
        """
        node.target.accept(self)
        for expr in node.arguments:
            expr.accept(self)

    def visit_constant_expr(self, node):
        """
        This function is called when visiting a constant, and by default does nothing.
        """

    def visit_boolean_expr(self, node):
        """
        This function is called when visiting a boolean literal, and by default does nothing.
        """

    def visit_ident_expr(self, node):
        """
        This function is called when visiting an identifier reference, and by default does nothing.
        """

    def visit_type(self, node):
        """
        This function is called when visiting a type reference, and by default does nothing.
        """

    def visit_builtin_expr(self, node):
        """
        This function is called when visiting a call to a built-in function, and by default does
        nothing, iterating onto the child.
        """
        node.target.accept(self)

    def visit_and_expr(self, node):
        """
        This function is called when visiting an application of the "and" operator, and by default
        does nothing, iterating onto the children.
        """
        node.left.accept(self)
        node.right.accept(self)

    def visit_or_expr(self, node):
        """
        This function is called when visiting an application of the "or" operator, and by default
        does nothing, iterating onto the children.
        """
        node.left.accept(self)
        node.right.accept(self)
