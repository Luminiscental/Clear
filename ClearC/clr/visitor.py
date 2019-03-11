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
        This function is called when visiting a value declaration, and by default does nothing.
        """

    def visit_print_stmt(self, node):
        """
        This function is called when visiting a print statement, and by default does nothing.
        """

    def visit_if_stmt(self, node):
        """
        This function is called when visiting an if statement, and by default does nothing.
        """

    def visit_expr_stmt(self, node):
        """
        This function is called when visiting an expression statement, and by default does nothing.
        """

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

    def visit_expr(self, node):
        """
        This function is called after visiting an expression, and by default does nothing.
        """

    def visit_unary_expr(self, node):
        """
        This function is called when visiting a unary expression, and by default does nothing.
        """

    def visit_binary_expr(self, node):
        """
        This function is called when visiting a binary expression, and by default does nothing.
        """

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

    def visit_builtin_expr(self, node):
        """
        This function is called when visiting a call to a built-in function, and by default does
        nothing.
        """

    def visit_and_expr(self, node):
        """
        This function is called when visiting an application of the "and" operator, and by default
        does nothing.
        """

    def visit_or_expr(self, node):
        """
        This function is called when visiting an application of the "or" operator, and by default
        does nothing.
        """
