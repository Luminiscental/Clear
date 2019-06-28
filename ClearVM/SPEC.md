# ClearVM specification

ClearVM is a stack based vm, when called with a module name `$ clr <name>` it will look for a file
`name.clr.b` and attempt to parse and run it.

## State

The VM has multiple pieces of state:

__Return Store__

The return store is a single value that is stored by the VM that can be accessed by the
`OP_SET_RETURN` and `OP_PUSH_RETURN` instructions. By default it is set to the nil value.

__Instruction Pointer__

The IP (instruction pointer) is a pointer to the next opcode in the program to execute. It can be
manipulated with jump instructions (`OP_JUMP`, `OP_JUMP_IF_FALSE`, `OP_LOOP`) or directly from a
value with `OP_LOAD_IP`.

__Frame Pointer__

The FP (frame pointer) is a pointer to a value on the stack. Conceptually this is the first value
in the current call frame. It can be manipulated by `OP_CALL` or `OP_LOAD_FP` instructions.

__Stack__

The stack is a [stack](https://en.wikipedia.org/wiki/Stack_%28abstract_data_type%29) of values that
gets manipulated by all instructions. Any value in use that isn't a global, a constant, or in the
return store, will be found on the stack.

__Globals__

The VM has an array of global values that can be accessed by index with the `OP_SET_GLOBAL` and
`OP_PUSH_GLOBAL` instructions.

__Constants__

The VM has an array of constant values loaded from the constant header that can be accessed by
index with the `OP_PUSH_CONST` instruction.

## Values

The values on the stack contain a type flag and a union of data specific to each type.

__Value Types__

- 0x0 (`VAL_BOOL`) : Boolean type values represent a `true` or `false` value. They can be created from
    `OP_PUSH_TRUE` or `OP_PUSH_FALSE` instructions.

- 0x1 (`VAL_NIL`) : Nil type values are all considered the same, representing a singleton `nil` value.
    They can be created from `OP_PUSH_NIL` instructions.

- 0x2 (`VAL_OBJ`) : Object type values are references to heap allocated objects, they contain a further
    flag for what type of object is referenced.

- 0x3 (`VAL_INT`) : Integer type values represent a 32-bit signed integer. They can be loaded as
    constants or as the result of arithmetic operations or the `OP_INT` cast instruction.

- 0x4 (`VAL_NUM`) : Number type values represent a 64-bit double-precision floating-point value. They
    can be loaded as constants or as the result of arithmetic operations or the `OP_NUM` cast
    instruction.

- 0x5 (`VAL_IP`) : IP (instruction pointer) type values represent a pointer to a part of the program
    being run. They can be created from `OP_FUNCTION` or `OP_CALL` instructions.

- 0x6 (`VAL_FP`) : FP (frame pointer) type values represent a pointer to a Value on the stack. They can
    be created from `OP_CALL` instructions.

__Object Types__

- 0x0 (`OBJ_STRING`) : string objects represent a UTF-8 string of characters. They can be loaded as
    constants or created from `OP_STR_CAT` or `OP_STR` instructions.

- 0x1 (`OBJ_STRUCT`) : struct objects contain an array of values with a known runtime length.
    They can be created from `OP_STRUCT` instructions.

- 0x2 (`OBJ_UPVALUE`) : upvalue objects contain a pointer to a referenced value, which is either on the
    stack or stored within the upvalue object. They can be created from `OP_REF_LOCAL`
    instructions.

## File format

Clear binary files have a simple format, with a header for constants followed by the program body.

### Header

The first byte is interpreted as an unsigned 8-bit integer, this is the number of constants in
the header (and can be 0). This is followed by a sequence of single byte flags describing the kind
of constant in front of a packed constant value. The following byte flags are allowed:

- 0x00 (`CONST_INT`) : this signifies a packed `int` constant; 4 bytes making a 32-bit signed integer.
- 0x01 (`CONST_NUM`) : this signifies a packed `num` constant; 8 bytes making a 64-bit
  double-precision floating point value.
- 0x02 (`CONST_STR`)  : this signifies a packed `str` constant; a byte interpreted unsigned as the
  length of the string followed by the bytes of the encoded string without a null terminator.

### Body

The body contains a sequence of opcodes (1 byte each) and arguments until the end of the file:

__Opcodes__

- 0x00 (`OP_PUSH_CONST`)

    _Parameters_: `index` (unsigned byte)

    _Initial Stack_: `...`

    _Final Stack_: `..., const`

    Given an argument `index`, pushes the constant value from that index into the
    constant header onto the stack. If the index is out of bounds this emits an error.

- 0x01 (`OP_PUSH_TRUE`)

    _Parameters_: none

    _Initial Stack_: `...`

    _Final Stack_: `..., true`

    Pushes a `true` boolean value onto the stack.

- 0x02 (`OP_PUSH_FALSE`)

    _Parameters_: none

    _Initial Stack_: `...`

    _Final Stack_: `..., false`

    Pushes a `false` boolean value onto the stack.

- 0x03 (`OP_PUSH_NIL`)

    _Parameters_: none

    _Initial Stack_: `...`

    _Final Stack_: `..., nil`

    Pushes a `nil` value onto the stack.

- 0x04 (`OP_SET_GLOBAL`)

    _Parameters_: `index` (unsigned byte)

    _Initial Stack_: `..., value`

    _Final Stack_: `...`

    Given an argument `index`, pops a value off the stack and sets the global value at the index to
    the popped value.

- 0x05 (`OP_PUSH_GLOBAL`)

    _Parameters_: `index` (unsigned byte)

    _Initial Stack_: `...`

    _Final Stack_: `..., global`

    Given an argument `index`, pushes the global value at the index onto the stack. If the global
    at the index hasn't been set yet this emits an error.

- 0x06 (`OP_SET_LOCAL`)

    _Parameters_: `index` (unsigned byte)

    _Initial Stack_: `..., value`

    _Final Stack_: `...`

    Given an argument `index`, pops a value off the stack and sets the local at the index (i.e. the
    value on the stack offset from the FP by the index) to the popped value. If the index is above
    the top of the stack this emits an error.

- 0x07 (`OP_PUSH_LOCAL`)

    _Parameters_: `index`

    _Initial Stack_: `...`

    _Final Stack_: `..., local`

    Given an argument `index`, pushes the local value at the index (i.e. the value on the stack
    offset from the FP by the index) onto the stack. If the index is above the top of the stack
    this emits an error.

- 0x08 (`OP_INT`)

    _Parameters_: none

    _Initial Stack_: `..., value`

    _Final Stack_: `..., int`

    Pops a value off the stack, and casts it to an `int` type value. If the popped value is a
    pointer type (i.e. `VAL_OBJ`, `VAL_IP`, `VAL_FP`) this emits an error.

    Effects:

    `VAL_BOOL` : `true` → `1`, `false` → `0`

    `VAL_NIL` : `nil` → `0`

    `VAL_INT` : `n` → `n`

    `VAL_NUM` : downcast with the same semantics as C cast from `double` to `int32_t`.

- 0x09 (`OP_BOOL`)

    _Parameters_: none

    _Initial Stack_: `..., value`

    _Final Stack_: `..., bool`

    Pops a value off the stack, and casts it to a `bool` type value. If the popped value is a
    pointer type (i.e. `VAL_OBJ`, `VAL_IP`, `VAL_FP`) this emits an error.

    Effects:

    `VAL_BOOL` : `b` → `b`

    `VAL_NIL` : `nil` → `false`

    `VAL_INT` : `n` → `n != 0`

    `VAL_NUM` : `x` → `x != 0.0`

- 0x0a (`OP_NUM`)

    _Parameters_: none

    _Initial Stack_: `..., value`

    _Final Stack_: `..., num`

    Pops a value off the stack, and casts it to a `num` type value. If the popped value is a
    pointer type (i.e. `VAL_OBJ`, `VAL_IP`, `VAL_FP`) this emits an error.

    Effects:

    `VAL_BOOL` : `true` → `1.0`, `false` → `0.0`

    `VAL_NIL` : `nil` → `0.0`

    `VAL_INT` : upcast with the same semantics as C cast from `int32_t` to `double`

    `VAL_NUM` : `x` → `x`

- 0x0b (`OP_STR`)

    _Parameters_: none

    _Initial Stack_: `..., value`

    _Final Stack_: `..., str`

    Pops a value off the stack, and pushes a representative string object for it. If the popped
    value is a pointer type (i.e. `VAL_OBJ`, `VAL_IP`, `VAL_FP`) this emits an error.

    Effects:

    `VAL_BOOL` : `true` → `"true"`, `false` → `"false"`

    `VAL_NIL` : `nil` → `"nil"`

    `VAL_INT` : displayed as an integer

    `VAL_NUM` : displayed to 7 decimal places

- 0x0c (`OP_CLOCK`)

    _Parameters_: none

    _Initial Stack_: `...`

    _Final Stack_: `..., time`

    Pushes a `num` type value for the number of seconds since the vm was launched.

- 0x0d (`OP_PRINT`)

    _Parameters_: none

    _Initial Stack_: `..., str`

    _Final Stack_: `...`

    Pops a `str` type value off the stack and prints it to stdout. If the value is not a string
    this emits an error.

- 0x0e (`OP_POP`)

    _Parameters_: none

    _Initial Stack_: `..., value`

    _Final Stack_: `...`

    Pops a value off the stack.

- 0x0f (`OP_SQUASH`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., b`

    Pops two values then pushes the second one back onto the stack.

- 0x10 (`OP_INT_NEG`)

    _Parameters_: none

    _Initial Stack_: `..., n`

    _Final Stack_: `..., -n`

    Pops an `int` type value off the stack, and pushes it's integer negation. If the value is not
    an integer value of the produced integer is undefined.

- 0x11 (`OP_NUM_NEG`)

    _Parameters_: none

    _Initial Stack_: `..., x`

    _Final Stack_: `..., -x`

    Pops a `num` type value off the stack, and pushes it's negation. If the value is not a number
    the value of the produced number is undefined.

- 0x12 (`OP_INT_ADD`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a + b`

    Pops an `int` value off the stack, and adds it to the `int` value below. If either value is not
    an integer the value of the produced integer is undefined.

- 0x13 (`OP_NUM_ADD`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a + b`

    Pops a `num` value off the stack, and adds it to the `num` value below. If either value is not
    a number the value of the produced number is undefined.

- 0x14 (`OP_INT_SUB`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a - b`

    Pops an `int` value off the stack, and subtracts it from the `int` value below. If either value is not
    an integer the value of the produced integer is undefined.

- 0x15 (`OP_NUM_SUB`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a - b`

    Pops a `num` value off the stack, and subtracts it from the `num` value below. If either value is not
    a number the value of the produced number is undefined.

- 0x16 (`OP_INT_MUL`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a * b`

    Pops an `int` value off the stack, and multiplies it with the `int` value below. If either value is not
    an integer the value of the produced integer is undefined.

- 0x17 (`OP_NUM_MUL`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a * b`

    Pops a `num` value off the stack, and multiplies it with the `num` value below. If either value is not
    a number the value of the produced number is undefined.

- 0x18 (`OP_INT_DIV`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a / b`

    Pops an `int` value off the stack, and divides the `int` value below by it (integer division). If either value is not
    an integer the value of the produced integer is undefined.

- 0x19 (`OP_MUL_DIV`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a / b`

    Pops a `num` value off the stack, and divides the `num` value below by it. If either value is not
    a number the value of the produced number is undefined.

- 0x1a (`OP_STR_CAT`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a + b`

    Pops two `str` values off the stack and pushes their concatenation. If either value is not a
    string this emits an error.

- 0x1b (`OP_NOT`)

    _Parameters_: none

    _Initial Stack_: `..., b`

    _Final Stack_: `..., !b`

    Pops a `bool` value off the stack and pushes its negation. If the value is not a boolean the
    value of the produced boolean is undefined.

- 0x1c (`OP_INT_LESS`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a < b`

    Pops two `int` values off the stack and pushes a boolean for whether the integer below is less
    than the integer above. If either value is not an integer the value of the produced boolean is
    undefined.

- 0x1d (`OP_NUM_LESS`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a < b`

    Pops two `num` values off the stack and pushes a boolean for whether the number below is less
    than the number above. If either value is not a number the value of the produced boolean is
    undefined.

- 0x1e (`OP_INT_GREATER`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a > b`

    Pops two `int` values off the stack and pushes a boolean for whether the integer below is
    greater than the integer above. If either value is not an integer the value of the produced
    boolean is undefined.

- 0x1f (`OP_NUM_GREATER`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a > b`

    Pops two `num` values off the stack and pushes a boolean for whether the number below is
    greater than the number above. If either value is not a number the value of the produced
    boolean is undefined.

- 0x20 (`OP_EQUAL`)

    _Parameters_: none

    _Initial Stack_: `..., a, b`

    _Final Stack_: `..., a == b`

    Pops two values off the stack and pushes a boolean for whether they are equal. Values of
    different types are unequal, numbers are compared with a precision of 7 decimal places, string
    objects are compared fully, and non-string pointer types are compared for identity.

- 0x21 (`OP_JUMP`)

    _Parameters_: `offset` (unsigned byte)

    _Initial Stack_: `...`

    _Final Stack_: `...`

    Increases the IP by the given offset. If the resulting IP is outside of the program code this
    emits an error.

- 0x22 (`OP_JUMP_IF_FALSE`)

    _Parameters_: `offset` (unsigned byte)

    _Initial Stack_: `..., flag`

    _Final Stack_: `...`

    Pops a bool value off the stack, if the boolean is false acts like `OP_JUMP`. If the value is
    not a boolean whether the jump occurs is undefined.

- 0x23 (`OP_LOOP`)

    _Parameters_: `offset` (unsigned byte)

    _Initial Stack_: `...`

    _Final Stack_: `...`

    Decreases the IP by the given offset. If the resulting IP is outside of the program code this
    emits an error.

- 0x24 (`OP_FUNCTION`)

    _Parameters_: `offset` (unsigned byte)

    _Initial Stack_: `...`

    _Final Stack_: `..., ip`

    Given an offset, pushes the current IP onto the stack then increments the IP by the offset.

- 0x25 (`OP_CALL`)

    _Parameters_: `args` (unsigned byte)

    _Initial Stack_: `..., arg0, arg1, ..., argn, ip`

    _Final Stack_: `..., ip, fp, arg0, arg1, ..., argn`

    Given a number of arguments, pops an IP followed by that many values off the stack, then pushes
    the current IP and FP followed by the arguments and loads the popped IP. If the top value is
    not an IP value this emits an error.

- 0x26 (`OP_LOAD_IP`)

    _Parameters_: none

    _Initial Stack_: `..., ip`

    _Final Stack_: `...`

    Pops an IP value off the stack and copies it into the vm's IP. If the value is not an IP this
    emits an error.

- 0x27 (`OP_LOAD_FP`)

    _Parameters_: none

    _Initial Stack_: `..., fp`

    _Final Stack_: `...`

    Pops an FP value off the stack and copies it into the vm's FP. If the value is not an FP this
    emits an error.

- 0x28 (`OP_SET_RETURN`)

    _Parameters_: none

    _Initial Stack_: `..., value`

    _Final Stack_: `...`

    Pops a value off the stack and puts it in the return store.

- 0x29 (`OP_PUSH_RETURN`)

    _Parameters_: none

    _Initial Stack_: `...`

    _Final Stack_: `..., return`

    Pushes the return store value onto the stack.

- 0x2a (`OP_STRUCT`)

    _Parameters_: `fields` (unsigned byte)

    _Initial Stack_: `..., arg0, arg1, ..., argn`

    _Final Stack_: `..., struct`

    Pops the given number of field values off the stack and pushes a struct of them.

- 0x2b (`OP_GET_FIELD`)

    _Parameters_: `index` (unsigned byte)

    _Initial Stack_: `..., struct`

    _Final Stack_: `..., field`

    Pops a struct value off the stack and pushes its field at the given index. If the popped value
    isn't a struct or the index is too large this emits an error.

- 0x2c (`OP_EXTRACT_FIELD`)

    _Parameters_: `offset` (unsigned byte), `index` (unsigned byte)

    _Initial Stack_: `..., struct, ...`

    _Final Stack_: `..., struct, ..., field`

    Peeks down the stack by the given offset and pushes the field of the peeked struct value at the
    given index. If the peeked value is not a struct or the index is too large this emits an error.

- 0x2d (`OP_SET_FIELD`)

    _Parameters_: `index` (unsigned byte)

    _Initial Stack_: `..., struct, value`

    _Final Stack_: `..., struct`

    Pops a value off the stack and sets the field at the given index of the struct below to it. If
    the value below isn't a struct or the index is too large this emits an error.

- 0x2e (`OP_REF_LOCAL`)

    _Parameters_: `index` (unsigned byte)

    _Initial Stack_: `...`

    _Final Stack_: `..., upvalue`

    Pushes an upvalue referencing the local at the given index (i.e. the value on the stack offset
    from the FP by the index). If the index is above the top of the stack this emits an error.

- 0x2f (`OP_DEREF`)

    _Parameters_: none

    _Initial Stack_: `..., upvalue`

    _Final Stack_: `..., value`

    Pops an upvalue and pushes its referenced value.

- 0x30 (`OP_SET_REF`)

    _Parameters_: none

    _Initial Stack_: `..., upvalue, value`

    _Final Stack_: `...`

    Pops a value then an upvalue and sets the upvalues reference to the popped value.

- 0x31 (`OP_IS_VAL_TYPE`)

    _Parameters_: `type`

    _Initial Stack_: `..., value`

    _Final Stack_: `..., value, bool`

    Peeks at the top of the stack and pushes a boolean for whether its type is equal to the
    argument.

- 0x32 (`OP_IS_OBJ_TYPE`)

    _Parameters_: `type`

    _Initial Stack_: `..., value`

    _Final Stack_: `..., value, bool`

    Peeks at the top of the stack and pushes a boolean for whether its object type is equal to the
    argument. If the value is not an object the value of the pushed boolean is undefined.

## Examples

// TODO: add
