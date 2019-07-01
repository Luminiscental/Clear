"""
Module containing definitions for a Clear ast and a base class for ast visitors.
"""

from typing import Union, List, Optional, Tuple, Dict

import clr.errors as er
import clr.lexer as lx
import clr.annotations as an
import clr.types as ts
import clr.bytecode as bc

# Visitor definitions:


class AstVisitor:
    """
    Base class for an ast visitor.
    """

    def __init__(self) -> None:
        self.errors = er.ErrorTracker()

    def start(self, node: "Ast") -> None:
        """
        Start visiting a tree.
        """

    def value_decl(self, node: "AstValueDecl") -> None:
        """
        Visit a value declaration node.
        """

    def binding(self, node: "AstBinding") -> None:
        """
        Visit a value binding node.
        """

    def func_decl(self, node: "AstFuncDecl") -> None:
        """
        Visit a function declaration node.
        """

    def param(self, node: "AstParam") -> None:
        """
        Visit a parameter declaration node.
        """

    def print_stmt(self, node: "AstPrintStmt") -> None:
        """
        Visit a print statement node.
        """

    def block_stmt(self, node: "AstBlockStmt") -> None:
        """
        Visit a block statement node.
        """

    def if_stmt(self, node: "AstIfStmt") -> None:
        """
        Visit an if statement node.
        """

    def while_stmt(self, node: "AstWhileStmt") -> None:
        """
        Visit a while statement node.
        """

    def return_stmt(self, node: "AstReturnStmt") -> None:
        """
        Visit a return statement node.
        """

    def expr_stmt(self, node: "AstExprStmt") -> None:
        """
        Visit an expression statement.
        """

    def unary_expr(self, node: "AstUnaryExpr") -> None:
        """
        Visit a unary expression node.
        """

    def binary_expr(self, node: "AstBinaryExpr") -> None:
        """
        Visit a binary expression node.
        """

    def int_expr(self, node: "AstIntExpr") -> None:
        """
        Visit an int literal.
        """

    def num_expr(self, node: "AstNumExpr") -> None:
        """
        Visit a num literal.
        """

    def str_expr(self, node: "AstStrExpr") -> None:
        """
        Visit a str literal.
        """

    def ident_expr(self, node: "AstIdentExpr") -> None:
        """
        Visit an identifier expression.
        """

    def bool_expr(self, node: "AstBoolExpr") -> None:
        """
        Visit a boolean expression.
        """

    def nil_expr(self, node: "AstNilExpr") -> None:
        """
        Visit a nil literal.
        """

    def case_expr(self, node: "AstCaseExpr") -> None:
        """
        Visit a case expression.
        """

    def call_expr(self, node: "AstCallExpr") -> None:
        """
        Visit a function call expression node.
        """

    def tuple_expr(self, node: "AstTupleExpr") -> None:
        """
        Visit a tuple expression node.
        """

    def lambda_expr(self, node: "AstLambdaExpr") -> None:
        """
        Visit a lambda expression.
        """

    def ident_type(self, node: "AstIdentType") -> None:
        """
        Visit an identifier type node.
        """

    def void_type(self, node: "AstVoidType") -> None:
        """
        Visit a void type node.
        """

    def func_type(self, node: "AstFuncType") -> None:
        """
        Visit a function type node.
        """

    def optional_type(self, node: "AstOptionalType") -> None:
        """
        Visit an optional type node.
        """

    def union_type(self, node: "AstUnionType") -> None:
        """
        Visit a union type node.
        """

    def tuple_type(self, node: "AstTupleType") -> None:
        """
        Visit a tuple type node.
        """


class DeepVisitor(AstVisitor):
    """
    Ast visitor that propogates to all nodes for a convenient base class.
    """

    def _decl(self, node: "AstDecl") -> None:
        pass

    def start(self, node: "Ast") -> None:
        for decl in node.decls:
            decl.accept(self)

    def value_decl(self, node: "AstValueDecl") -> None:
        for binding in node.bindings:
            binding.accept(self)
        if node.val_type:
            node.val_type.accept(self)
        node.val_init.accept(self)
        self._decl(node)

    def func_decl(self, node: "AstFuncDecl") -> None:
        node.binding.accept(self)
        for param in node.params:
            param.accept(self)
        node.return_type.accept(self)
        node.block.accept(self)
        self._decl(node)

    def param(self, node: "AstParam") -> None:
        node.param_type.accept(self)

    def print_stmt(self, node: "AstPrintStmt") -> None:
        if node.expr:
            node.expr.accept(self)
        self._decl(node)

    def block_stmt(self, node: "AstBlockStmt") -> None:
        for decl in node.decls:
            decl.accept(self)
        self._decl(node)

    def if_stmt(self, node: "AstIfStmt") -> None:
        node.if_part[0].accept(self)
        node.if_part[1].accept(self)
        for cond, block in node.elif_parts:
            cond.accept(self)
            block.accept(self)
        if node.else_part:
            node.else_part.accept(self)
        self._decl(node)

    def while_stmt(self, node: "AstWhileStmt") -> None:
        if node.cond:
            node.cond.accept(self)
        node.block.accept(self)
        self._decl(node)

    def return_stmt(self, node: "AstReturnStmt") -> None:
        if node.expr:
            node.expr.accept(self)
        self._decl(node)

    def expr_stmt(self, node: "AstExprStmt") -> None:
        node.expr.accept(self)
        self._decl(node)

    def unary_expr(self, node: "AstUnaryExpr") -> None:
        node.target.accept(self)

    def binary_expr(self, node: "AstBinaryExpr") -> None:
        node.left.accept(self)
        node.right.accept(self)

    def case_expr(self, node: "AstCaseExpr") -> None:
        node.target.accept(self)
        node.binding.accept(self)
        for case_type, case_value in node.cases:
            case_type.accept(self)
            case_value.accept(self)
        if node.fallback:
            node.fallback.accept(self)

    def call_expr(self, node: "AstCallExpr") -> None:
        node.function.accept(self)
        for arg in node.args:
            arg.accept(self)

    def tuple_expr(self, node: "AstTupleExpr") -> None:
        for expr in node.exprs:
            expr.accept(self)

    def lambda_expr(self, node: "AstLambdaExpr") -> None:
        for param in node.params:
            param.accept(self)
        node.value.accept(self)

    def func_type(self, node: "AstFuncType") -> None:
        for param in node.params:
            param.accept(self)
        node.return_type.accept(self)

    def optional_type(self, node: "AstOptionalType") -> None:
        node.target.accept(self)

    def union_type(self, node: "AstUnionType") -> None:
        for subtype in node.types:
            subtype.accept(self)

    def tuple_type(self, node: "AstTupleType") -> None:
        for subtype in node.types:
            subtype.accept(self)


class ScopeVisitor(DeepVisitor):
    """
    Ast visitor base class to keep track of the current scope.
    """

    def __init__(self) -> None:
        super().__init__()
        self._scopes: List["AstScope"] = []

    def _get_scope(self) -> "AstScope":
        return self._scopes[-1]

    def _push_scope(self, node: "AstScope") -> None:
        self._scopes.append(node)

    def _pop_scope(self) -> None:
        self._scopes.pop()

    def start(self, node: "Ast") -> None:
        self._push_scope(node)
        super().start(node)
        self._pop_scope()

    def func_decl(self, node: "AstFuncDecl") -> None:
        node.binding.accept(self)
        self._push_scope(node.block)
        for param in node.params:
            param.accept(self)
        # Visit the block manually so it doesn't get an extra scope
        for decl in node.block.decls:
            decl.accept(self)
        self._pop_scope()
        self._decl(node)

    def block_stmt(self, node: "AstBlockStmt") -> None:
        self._push_scope(node)
        # Don't delegate to super, we want _decl to be called in the right scope
        for decl in node.decls:
            decl.accept(self)
        self._pop_scope()
        self._decl(node)

    def case_expr(self, node: "AstCaseExpr") -> None:
        node.target.accept(self)
        self._push_scope(node)
        node.binding.accept(self)
        for case_type, case_value in node.cases:
            case_type.accept(self)
            case_value.accept(self)
        if node.fallback:
            node.fallback.accept(self)
        self._pop_scope()

    def lambda_expr(self, node: "AstLambdaExpr") -> None:
        self._push_scope(node)
        super().lambda_expr(node)
        self._pop_scope()


AstFunction = Union["AstFuncDecl", "AstLambdaExpr"]


class FunctionVisitor(ScopeVisitor):
    """
    Ast visitor base class to keep track of the current function and scope.
    """

    def __init__(self) -> None:
        super().__init__()
        self._functions: List[AstFunction] = []

    def _get_function(self) -> AstFunction:
        return self._functions[-1]

    def _push_function(self, function: AstFunction) -> None:
        self._functions.append(function)

    def _pop_function(self) -> None:
        self._functions.pop()

    def func_decl(self, node: "AstFuncDecl") -> None:
        node.binding.accept(self)
        self._push_function(node)
        # Don't delegate to super, we want _decl to be called in the right scope
        for param in node.params:
            param.accept(self)
        node.return_type.accept(self)
        node.block.accept(self)
        self._pop_function()
        self._decl(node)

    def lambda_expr(self, node: "AstLambdaExpr") -> None:
        self._push_function(node)
        super().lambda_expr(node)
        self._pop_function()


# Node definitions:

# Base node types:


class AstNode:
    """
    Base class for an ast node. All nodes must be able to accept an ast visitor.
    """

    def __init__(self, region: er.SourceView) -> None:
        self.region = region

    def accept(self, visitor: AstVisitor) -> None:
        """
        Accept a visitor to this node, calling the relevant method of the visitor.
        """
        raise NotImplementedError


class AstTyped(AstNode):
    """
    Base class for nodes with type annotations.
    """

    def __init__(self, region: er.SourceView) -> None:
        super().__init__(region)
        self.type_annot = ts.UNRESOLVED

    def accept(self, visitor: AstVisitor) -> None:
        raise NotImplementedError


class AstIndexed(AstNode):
    """
    Base class for nodes with index annotations.
    """

    def __init__(self, region: er.SourceView) -> None:
        super().__init__(region)
        self.index_annot = an.IndexAnnot(value=-1, kind=an.IndexAnnotType.UNRESOLVED)

    def accept(self, visitor: AstVisitor) -> None:
        raise NotImplementedError


class AstType(AstTyped):
    """
    Base class for types to help mypy.
    """

    def accept(self, visitor: AstVisitor) -> None:
        raise NotImplementedError


class AstExpr(AstTyped):
    """
    Base class for expressions to help mypy.
    """

    def accept(self, visitor: AstVisitor) -> None:
        raise NotImplementedError


class AstScope(AstNode):
    """
    Base class for a node with scope.
    """

    def __init__(self, region: er.SourceView) -> None:
        super().__init__(region)
        self.names: Dict[str, AstIdentRef] = {}

    def accept(self, visitor: AstVisitor) -> None:
        raise NotImplementedError


class AstDecl(AstNode):
    """
    Base class for declarations, annotated with return possibilities and scope.
    """

    def __init__(self, region: er.SourceView) -> None:
        super().__init__(region)
        self.return_annot = an.ReturnAnnot.NEVER
        self.scope: Optional[AstScope] = None

    def accept(self, visitor: AstVisitor) -> None:
        raise NotImplementedError


AstStmt = Union[
    "AstPrintStmt",
    "AstBlockStmt",
    "AstIfStmt",
    "AstWhileStmt",
    "AstReturnStmt",
    "AstExprStmt",
]

# Specific nodes:


class Ast(AstScope):
    """
    The root ast node.
    """

    def __init__(self, decls: List[AstDecl], region: er.SourceView) -> None:
        super().__init__(region)
        self.decls = decls
        # Annotations
        self.sequence: List[AstDecl] = []

    def accept(self, visitor: AstVisitor) -> None:
        visitor.start(self)


class AstBinding(AstTyped, AstIndexed):
    """
    Ast node for a value binding.
    """

    def __init__(self, name: str, region: er.SourceView) -> None:
        super().__init__(region)
        self.name = name

    def accept(self, visitor: AstVisitor) -> None:
        visitor.binding(self)


class AstValueDecl(AstDecl, AstTyped):
    """
    Ast node for a value declaration.
    """

    def __init__(
        self,
        bindings: List[AstBinding],
        val_type: Optional[AstType],
        val_init: AstExpr,
        region: er.SourceView,
    ):
        super().__init__(region)
        self.bindings = bindings
        self.val_type = val_type
        self.val_init = val_init

    def accept(self, visitor: AstVisitor) -> None:
        visitor.value_decl(self)


class AstParam(AstTyped, AstIndexed):
    """
    Ast node for a parameter declaration.
    """

    def __init__(self, param_type: AstType, param_name: lx.Token) -> None:
        super().__init__(er.SourceView.range(param_type.region, param_name.lexeme))
        self.param_type = param_type
        self.param_name = str(param_name)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.param(self)


class AstFuncDecl(AstDecl, AstTyped, AstIndexed):
    """
    Ast node for a function declaration.
    """

    def __init__(
        self,
        binding: AstBinding,
        params: List[AstParam],
        return_type: AstType,
        block: "AstBlockStmt",
        region: er.SourceView,
    ) -> None:
        super().__init__(region)
        self.binding = binding
        self.params = params
        self.return_type = return_type
        self.block = block
        # Annotations
        self.upvalues: List[AstIdentRef] = []
        self.upvalue_indices: List[an.IndexAnnot] = []

    def accept(self, visitor: AstVisitor) -> None:
        visitor.func_decl(self)


class AstPrintStmt(AstDecl):
    """
    Ast node for a print statement.
    """

    def __init__(self, expr: Optional[AstExpr], region: er.SourceView) -> None:
        super().__init__(region)
        self.expr = expr

    def accept(self, visitor: AstVisitor) -> None:
        visitor.print_stmt(self)


class AstBlockStmt(AstDecl, AstScope):
    """
    Ast node for a block statement.
    """

    def __init__(self, decls: List[AstDecl], region: er.SourceView) -> None:
        super().__init__(region)
        self.decls = decls
        # Annotations
        self.sequence: List[AstDecl] = []

    def accept(self, visitor: AstVisitor) -> None:
        visitor.block_stmt(self)


class AstIfStmt(AstDecl):
    """
    Ast node for an if statement.
    """

    def __init__(
        self,
        if_part: Tuple[AstExpr, AstBlockStmt],
        elif_parts: List[Tuple[AstExpr, AstBlockStmt]],
        else_part: Optional[AstBlockStmt],
        region: er.SourceView,
    ) -> None:
        super().__init__(region)
        self.if_part = if_part
        self.elif_parts = elif_parts
        self.else_part = else_part

    def accept(self, visitor: AstVisitor) -> None:
        visitor.if_stmt(self)


class AstWhileStmt(AstDecl):
    """
    Ast node for a while statement.
    """

    def __init__(
        self, cond: Optional[AstExpr], block: AstBlockStmt, region: er.SourceView
    ) -> None:
        super().__init__(region)
        self.cond = cond
        self.block = block

    def accept(self, visitor: AstVisitor) -> None:
        visitor.while_stmt(self)


class AstReturnStmt(AstDecl):
    """
    Ast node for a return statement.
    """

    def __init__(self, expr: Optional[AstExpr], region: er.SourceView) -> None:
        super().__init__(region)
        self.expr = expr

    def accept(self, visitor: AstVisitor) -> None:
        visitor.return_stmt(self)


class AstExprStmt(AstDecl):
    """
    Ast node for an expression statement.
    """

    def __init__(self, expr: AstExpr, region: er.SourceView) -> None:
        super().__init__(region)
        self.expr = expr

    def accept(self, visitor: AstVisitor) -> None:
        visitor.expr_stmt(self)


class AstUnaryExpr(AstExpr):
    """
    Ast node for a unary expression.
    """

    def __init__(
        self, operator: lx.Token, target: AstExpr, region: er.SourceView
    ) -> None:
        super().__init__(region)
        self.operator = operator
        self.target = target
        self.opcodes: List[bc.Instruction] = []

    def accept(self, visitor: AstVisitor) -> None:
        visitor.unary_expr(self)


class AstBinaryExpr(AstExpr):
    """
    Ast node for a binary expression.
    """

    def __init__(
        self, operator: lx.Token, left: AstExpr, right: AstExpr, region: er.SourceView
    ) -> None:
        super().__init__(region)
        self.operator = operator
        self.left = left
        self.right = right
        self.opcodes: List[bc.Instruction] = []

    def accept(self, visitor: AstVisitor) -> None:
        visitor.binary_expr(self)


class AstIntExpr(AstExpr):
    """
    Ast node for an int literal.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__(literal.lexeme)
        self.literal = str(literal)
        self.value = int(self.literal[:-1])

    def accept(self, visitor: AstVisitor) -> None:
        visitor.int_expr(self)


class AstNumExpr(AstExpr):
    """
    Ast node for a num literal.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__(literal.lexeme)
        self.literal = str(literal)
        self.value = float(self.literal)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.num_expr(self)


class AstStrExpr(AstExpr):
    """
    Ast node for a str literal.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__(literal.lexeme)
        self.literal = str(literal)
        self.value = self.literal[1:-1]

    def accept(self, visitor: AstVisitor) -> None:
        visitor.str_expr(self)


# Type alias for identifier declarations
AstIdentRef = Union[AstBinding, AstParam]


class AstIdentExpr(AstExpr, AstIndexed):
    """
    Ast node for an identifier expression.
    """

    def __init__(self, token: lx.Token) -> None:
        super().__init__(token.lexeme)
        self.name = str(token)
        # Annotations
        self.ref: Optional[AstIdentRef] = None

    def accept(self, visitor: AstVisitor) -> None:
        visitor.ident_expr(self)


class AstBoolExpr(AstExpr):
    """
    Ast node for a boolean expression.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__(literal.lexeme)
        self.value = str(literal) == "true"

    def accept(self, visitor: AstVisitor) -> None:
        visitor.bool_expr(self)


class AstNilExpr(AstExpr):
    """
    Ast node for a nil literal.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__(literal.lexeme)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.nil_expr(self)


class AstCaseExpr(AstExpr, AstScope):
    """
    Ast node for a case expression.
    """

    def __init__(
        self,
        target: AstExpr,
        binding: AstBinding,
        cases: List[Tuple[AstType, AstExpr]],
        fallback: Optional[AstExpr],
        region: er.SourceView,
    ) -> None:
        super().__init__(region)
        self.target = target
        self.binding = binding
        self.cases = cases
        self.fallback = fallback

    def accept(self, visitor: AstVisitor) -> None:
        visitor.case_expr(self)


class AstCallExpr(AstExpr):
    """
    Ast node for a function call expression.
    """

    def __init__(
        self, function: AstExpr, args: List[AstExpr], region: er.SourceView
    ) -> None:
        super().__init__(region)
        self.function = function
        self.args = args

    def accept(self, visitor: AstVisitor) -> None:
        visitor.call_expr(self)


class AstTupleExpr(AstExpr):
    """
    Ast node for a tuple expression.
    """

    def __init__(self, exprs: Tuple[AstExpr, ...], region: er.SourceView) -> None:
        super().__init__(region)
        self.exprs = exprs

    def accept(self, visitor: AstVisitor) -> None:
        visitor.tuple_expr(self)


class AstLambdaExpr(AstExpr, AstScope):
    """
    Ast node for a lambda expression.
    """

    def __init__(
        self, params: List[AstParam], value: AstExpr, region: er.SourceView
    ) -> None:
        super().__init__(region)
        self.params = params
        self.value = value
        self.region = region
        # Annotations
        self.upvalues: List[AstIdentRef] = []
        self.upvalue_indices: List[an.IndexAnnot] = []

    def accept(self, visitor: AstVisitor) -> None:
        visitor.lambda_expr(self)


class AstIdentType(AstType):
    """
    Ast node for an atomic type.
    """

    def __init__(self, token: lx.Token) -> None:
        super().__init__(token.lexeme)
        self.name = str(token)
        # Annotations
        self.ref: Optional[AstIdentRef] = None

    def accept(self, visitor: AstVisitor) -> None:
        visitor.ident_type(self)


class AstVoidType(AstType):
    """
    Ast node for a void type.
    """

    def __init__(self, token: lx.Token) -> None:
        super().__init__(token.lexeme)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.void_type(self)


class AstFuncType(AstType):
    """
    Ast node for a function type.
    """

    def __init__(
        self, params: List[AstType], return_type: AstType, region: er.SourceView
    ) -> None:
        super().__init__(region)
        self.params = params
        self.return_type = return_type

    def accept(self, visitor: AstVisitor) -> None:
        visitor.func_type(self)


class AstOptionalType(AstType):
    """
    Ast node for an optional type.
    """

    def __init__(self, target: AstType, region: er.SourceView) -> None:
        super().__init__(region)
        self.target = target

    def accept(self, visitor: AstVisitor) -> None:
        visitor.optional_type(self)


class AstUnionType(AstType):
    """
    Ast node for a union type.
    """

    def __init__(self, types: List[AstType], region: er.SourceView) -> None:
        super().__init__(region)
        self.types = types

    def accept(self, visitor: AstVisitor) -> None:
        visitor.union_type(self)


class AstTupleType(AstType):
    """
    Ast node for a tuple type.
    """

    def __init__(self, types: Tuple[AstType, ...], region: er.SourceView) -> None:
        super().__init__(region)
        self.types = types

    def accept(self, visitor: AstVisitor) -> None:
        visitor.tuple_type(self)
