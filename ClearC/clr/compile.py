from clr.tokens import TokenType, token_info, tokenize
from clr.errors import emit_error
from clr.assemble import assemble, assembled_size
from clr.constants import Constants, ClrNum, ClrInt, ClrUint, ClrStr
from clr.values import OpCode, Precedence, pratt_table, DEBUG


class LocalVariables:
    def __init__(self):
        self.scopes = []
        self.level = -1
        self.index = 0

    def scoped(self):
        return self.level > -1

    def current_scope(self):
        if not self.scoped():
            emit_error("Global scope is not local!")()
        return self.scopes[self.level]

    def push_scope(self):
        self.scopes.append({})
        self.level += 1
        if DEBUG:
            print(f"Pushed scope, level is now {self.level}")

    def pop_scope(self):
        if not self.scoped():
            emit_error("Cannot pop scope at global scope!")()
        popped_scope = self.current_scope()
        if popped_scope:
            self.index = min(popped_scope.values())
        del self.scopes[self.level]
        self.level -= 1
        if DEBUG:
            print(f"Popped scope, level is now {self.level}, index is now {self.index}")

    def get_name(self, name):
        if not self.scoped():
            return None
        return self.current_scope().get(name, None)

    def add_name(self, name):
        if not self.scoped():
            emit_error("Cannot define local variable in global scope!")()
        index = self.get_name(name)
        if index is not None:
            return index
        new_index = self.index
        self.index += 1
        self.current_scope()[name] = new_index
        if DEBUG:
            print(
                f"Defined local name {name} at level {self.level}, index is now {self.index}"
            )
        return new_index


class GlobalVariables:
    def __init__(self):
        self.indices = {}
        self.index = 0

    def get_name(self, name):
        return self.indices.get(name, None)

    def add_name(self, name):
        index = self.get_name(name)
        if index is not None:
            return index
        new_index = self.index
        self.index += 1
        self.indices[name] = new_index
        if DEBUG:
            print(f"Defined global name {name}, index is now {self.index}")
        return new_index


class Program:
    def __init__(self):
        self.code_list = []
        self.global_variables = GlobalVariables()
        self.local_variables = LocalVariables()

    def load_constant(self, constant):
        self.code_list.append(OpCode.LOAD_CONST)
        self.code_list.append(constant)

    def simple_op(self, opcode):
        self.code_list.append(opcode)

    def push_scope(self):
        self.local_variables.push_scope()
        self.simple_op(OpCode.PUSH_SCOPE)

    def pop_scope(self):
        self.local_variables.pop_scope()
        self.simple_op(OpCode.POP_SCOPE)

    def define_name(self, name):
        if self.local_variables.scoped():
            index = self.local_variables.add_name(name)
            self.code_list.append(OpCode.DEFINE_LOCAL)
        else:
            index = self.global_variables.add_name(name)
            self.code_list.append(OpCode.DEFINE_GLOBAL)
        self.code_list.append(index)

    def load_name(self, name, err):
        opcode = OpCode.LOAD_LOCAL
        index = self.local_variables.get_name(name)
        if index is None:
            opcode = OpCode.LOAD_GLOBAL
            index = self.global_variables.get_name(name)
            if index is None:
                err()
        self.code_list.append(opcode)
        self.code_list.append(index)

    def begin_jump(self, conditional=False):
        self.code_list.append(OpCode.JUMP_IF_NOT if conditional else OpCode.JUMP)
        index = len(self.code_list)
        if DEBUG:
            print(f"Defining a jump from {index}")
        temp_offset = ClrUint(0)
        self.code_list.append(temp_offset)
        return index

    def end_jump(self, jump_ref):
        contained = self.code_list[jump_ref + 1 :]
        offset = assembled_size(contained)
        if DEBUG:
            print(f"Jump from index set with offset {offset}")
        self.code_list[jump_ref] = ClrUint(offset)

    def flush(self):
        return self.code_list


class Cursor:
    def __init__(self, tokens):
        self.index = 0
        self.tokens = tokens
        self.constants = Constants()
        self.program = Program()

    def get_current(self):
        return self.tokens[self.index]

    def get_prev(self):
        return self.tokens[self.index - 1]

    def current_info(self):
        return token_info(self.get_current())

    def prev_info(self):
        return token_info(self.get_prev())

    def advance(self):
        self.index += 1

    def check(self, token_type):
        return self.get_current().token_type == token_type

    def match(self, expected_type):
        if not self.check(expected_type):
            return False
        self.advance()
        return True

    def consume(self, expected_type, message):
        if not self.match(expected_type):
            emit_error(message)()

    def flush(self):
        return self.constants.flush() + self.program.flush()


class Parser(Cursor):
    def get_rule(self, token):
        return pratt_table(
            self, err=emit_error(f"Expected expression! {token_info(token)}")
        )[token.token_type]

    def current_precedence(self):
        return self.get_rule(self.get_current()).precedence

    def finish_builtin(self):
        builtin = self.get_prev()
        self.consume(
            TokenType.LEFT_PAREN,
            f"Expected parameter to built-in function! {self.prev_info()}",
        )
        self.finish_grouping()
        {
            TokenType.TYPE: lambda: self.program.simple_op(OpCode.TYPE),
            TokenType.INT: lambda: self.program.simple_op(OpCode.INT),
            TokenType.BOOL: lambda: self.program.simple_op(OpCode.BOOL),
            TokenType.NUM: lambda: self.program.simple_op(OpCode.NUM),
            TokenType.STR: lambda: self.program.simple_op(OpCode.STR),
        }.get(
            builtin.token_type,
            emit_error(f"Expected built-in function! {self.prev_info()}"),
        )()

    def finish_boolean(self):
        token = self.get_prev()
        err = emit_error(f"Expected boolean token! {self.prev_info()}")
        {
            TokenType.TRUE: lambda: self.program.simple_op(OpCode.TRUE),
            TokenType.FALSE: lambda: self.program.simple_op(OpCode.FALSE),
        }.get(token.token_type, err)()

    def finish_number(self):
        token = self.get_prev()
        if token.token_type != TokenType.NUMBER:
            emit_error(f"Expected number token! {self.prev_info()}")()
        if self.match(TokenType.INTEGER_SUFFIX):
            try:
                value = ClrInt(token.lexeme)
            except ValueError:
                emit_error(f"Integer literal must be an integer! {self.prev_info()}")()
        else:
            try:
                value = ClrNum(token.lexeme)
            except ValueError:
                emit_error(f"Number literal must be a number! {self.prev_info()}")()
        const_index = self.constants.add(value)
        self.program.load_constant(const_index)

    def finish_string(self):
        token = self.get_prev()
        if token.token_type != TokenType.STRING:
            emit_error(f"Expected string token! {self.prev_info()}")()

        total = [token]
        while self.match(TokenType.STRING):
            total.append(self.get_prev())

        string = ClrStr('"'.join(map(lambda t: t.lexeme[1:-1], total)))
        const_index = self.constants.add(string)
        self.program.load_constant(const_index)

    def consume_precedence(self, precedence):
        self.advance()
        self.get_rule(self.get_prev()).prefix()
        while precedence <= self.current_precedence():
            self.advance()
            self.get_rule(self.get_prev()).infix()

    def finish_grouping(self):
        self.consume_expression()
        self.consume(
            TokenType.RIGHT_PAREN, f"Expected ')' after expression! {self.prev_info()}"
        )

    def finish_unary(self):
        op_token = self.get_prev()
        self.consume_precedence(Precedence.UNARY)
        {
            TokenType.MINUS: lambda: self.program.simple_op(OpCode.NEGATE),
            TokenType.BANG: lambda: self.program.simple_op(OpCode.NOT),
        }.get(
            op_token.token_type,
            emit_error(f"Expected unary operator! {self.prev_info()}"),
        )()

    def finish_binary(self):
        op_token = self.get_prev()
        rule = self.get_rule(op_token)
        self.consume_precedence(rule.precedence.next())
        {
            TokenType.PLUS: lambda: self.program.simple_op(OpCode.ADD),
            TokenType.MINUS: lambda: self.program.simple_op(OpCode.SUBTRACT),
            TokenType.STAR: lambda: self.program.simple_op(OpCode.MULTIPLY),
            TokenType.SLASH: lambda: self.program.simple_op(OpCode.DIVIDE),
            TokenType.EQUAL_EQUAL: lambda: self.program.simple_op(OpCode.EQUAL),
            TokenType.BANG_EQUAL: lambda: self.program.simple_op(OpCode.NEQUAL),
            TokenType.LESS: lambda: self.program.simple_op(OpCode.LESS),
            TokenType.GREATER_EQUAL: lambda: self.program.simple_op(OpCode.NLESS),
            TokenType.GREATER: lambda: self.program.simple_op(OpCode.GREATER),
            TokenType.LESS_EQUAL: lambda: self.program.simple_op(OpCode.NGREATER),
        }.get(
            op_token.token_type,
            emit_error(f"Expected binary operator! {self.prev_info()}"),
        )()

    def consume_expression(self):
        self.consume_precedence(Precedence.ASSIGNMENT)

    def finish_print_statement(self):
        if self.match(TokenType.SEMICOLON):  # Blank print statement
            self.program.simple_op(OpCode.PRINT_BLANK)
        else:
            self.consume_expression()
            self.consume(
                TokenType.SEMICOLON,
                f"Expected semicolon after statement! {self.prev_info()}",
            )
            self.program.simple_op(OpCode.PRINT)

    def consume_expression_statement(self):
        self.consume_expression()
        self.consume(TokenType.SEMICOLON, f"Expected statement! {self.prev_info()}")
        self.program.simple_op(OpCode.POP)

    def finish_if_statement(self):
        self.consume_expression()
        if_jump = self.program.begin_jump(conditional=True)
        self.consume(
            TokenType.LEFT_BRACE, f"If statement requires a block! {self.prev_info()}"
        )
        self.finish_block()
        if self.match(TokenType.ELSE):
            else_jump = self.program.begin_jump()
            self.program.end_jump(if_jump)
            self.consume(
                TokenType.LEFT_BRACE,
                f"Else branch requires a block! {self.prev_info()}",
            )
            self.finish_block()
            self.program.end_jump(else_jump)
        else:
            self.program.end_jump(if_jump)

    def consume_statement(self):
        if self.match(TokenType.PRINT):
            self.finish_print_statement()
        elif self.match(TokenType.LEFT_BRACE):
            self.finish_block()
        elif self.match(TokenType.IF):
            self.finish_if_statement()
        # TODO: for
        else:
            self.consume_expression_statement()

    def consume_variable(self, message):
        self.consume(TokenType.IDENTIFIER, message)
        return self.get_prev().lexeme

    def finish_variable_declaration(self):
        name = self.consume_variable(f"Expected variable name! {self.prev_info()}")
        self.consume(
            TokenType.EQUAL, f"Expected variable initializer! {self.prev_info()}"
        )
        self.consume_expression()
        self.consume(
            TokenType.SEMICOLON,
            f"Expected semicolon after statement! {self.prev_info()}",
        )
        self.program.define_name(name)

    def finish_variable_reference(self):
        token = self.get_prev()
        if token.token_type != TokenType.IDENTIFIER:
            emit_error(f"Expected variable! {self.prev_info()}")()
        self.program.load_name(
            token.lexeme,
            emit_error(f"Reference to undefined identifier! {self.prev_info()}"),
        )

    def consume_declaration(self):
        if self.match(TokenType.VAL):
            self.finish_variable_declaration()
        else:
            self.consume_statement()

    def finish_block(self):
        self.program.push_scope()
        while not self.match(TokenType.RIGHT_BRACE):
            self.consume_declaration()
        self.program.pop_scope()


def parse_source(source):

    tokens = tokenize(source)
    if DEBUG:
        print("Tokens:")
        print(" ".join([token.lexeme for token in tokens]))
    parser = Parser(tokens)
    while not parser.match(TokenType.EOF):
        parser.consume_declaration()
    return assemble(parser.flush())
