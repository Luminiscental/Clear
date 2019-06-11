#ifndef clearvm_bytecode_h
#define clearvm_bytecode_h

#include "common.h"

typedef enum {

    CONST_INT = 0,
    CONST_NUM = 1,
    CONST_STR = 2,
    CONST_COUNT = 3

} ConstantType;

typedef enum {

    // Constant generation
    OP_PUSH_CONST = 0, // op <u8> - pushes constant from index

    OP_PUSH_TRUE = 1,  // op - pushes true
    OP_PUSH_FALSE = 2, // op - pushes false

    OP_PUSH_NIL = 3, // op - pushes nil

    // Variables
    OP_SET_GLOBAL = 4,  // op <u8> - pops value and sets as global at index
    OP_PUSH_GLOBAL = 5, // op <u8> - pushes global at index

    OP_SET_LOCAL = 6,  // op <u8> - pops value and sets as local at index
    OP_PUSH_LOCAL = 7, // op <u8> - pushes local at index

    // Built-ins
    OP_INT = 8,  // op - pops value and converts to int
    OP_BOOL = 9, // op - pops value and converts to bool
    OP_NUM = 10, // op - pops value and converts to num
    OP_STR = 11, // op - pops value and converts to str

    OP_CLOCK = 12, // op - pushes clock value as num in seconds
    OP_PRINT = 13, // op - pops value and prints it on a line

    // Actions
    OP_POP = 14, // op - pops value

    // Arithmetic operators
    OP_INT_NEG = 15, // op - replaces top value with its int negation
    OP_NUM_NEG = 16, // op - replaces top value with its num negation

    OP_INT_ADD = 17, // op - pops two values and pushes their int sum
    OP_NUM_ADD = 18, // op - pops two values and pushes their num sum

    OP_INT_SUB = 19, // op - pops two values and pushes their int difference
    OP_NUM_SUB = 20, // op - pops two values and pushes their num difference

    OP_INT_MUL = 21, // op - pops two values and pushes their int product
    OP_NUM_MUL = 22, // op - pops two values and pushes their num product

    OP_INT_DIV = 23, // op - pops two values and pushes their int ratio
    OP_NUM_DIV = 24, // op - pops two values and pushes their num ratio

    OP_STR_CAT = 25, // op - pops two values and pushes their str concatenation

    OP_NOT = 26, // op - pops a value and pushes its boolean negation

    // Comparison operators
    OP_INT_LESS = 27, // op - pops two values and pushes a boolean for if the
                      // lower int is less
    OP_NUM_LESS = 28, // op - pops two values and pushes a boolean for if the
                      // lower num is less

    OP_INT_GREATER = 29, // op - pops two values and pushes a boolean for if the
                         // lower int is greater
    OP_NUM_GREATER = 30, // op - pops two values and pushes a boolean for if the
                         // lower num is greater

    OP_EQUAL = 31, // op - pops two values and pushes a boolean for whether they
                   // are equal

    // Control flow
    OP_JUMP = 32,          // op <u8> - moves the ip forward by the given offset
    OP_JUMP_IF_FALSE = 33, // op <u8> - pops the stack and moves the ip forward
                           // by the given offset if the popped value is false

    OP_LOOP = 34, // op <u8> - moves the ip backward by the given offset

    // Functions
    OP_FUNCTION =
        35, // op <u8> - pushes an ip value pointing to the next instruction
            // onto the stack and moves the ip forward by the given offset
    OP_CALL = 36, // op <u8> - pops an ip off the stack, then the given number
                  // of arguments, then pushes the current ip and fp and the
                  // arguments onto the stack and loads the popped ip
    OP_LOAD_IP = 37, // op - pops ip and copies it into the vm
    OP_LOAD_FP = 38, // op - pops fp and copies it into the vm
    OP_SET_RETURN =
        39, // op - pops a value off the stack and puts it in the return store
    OP_PUSH_RETURN = 40, // op - pushes the return store onto the stack

    // Structs
    OP_STRUCT = 41, // op <u8> - pops the given number of values off the stack
                    // and pushes a struct of them
    OP_GET_FIELD = 42, // op <u8> - pops a value off the stack and pushes its
                       // struct field at the given index
    OP_GET_FIELDS =
        43, // op <u8> [<u8>] - Takes a number of fields followed by the indices
            // of those fields, pops a value and pushes its fields at those
            // indices onto the stack, last index on top
    OP_SET_FIELD =
        44, // op <u8> - pops a value off the stack, then sets the struct field
            // of the remaining value at the given index to it

    OP_COUNT = 45

} OpCode;

Result disassembleCode(uint8_t *code, size_t length);

#endif
