
#include "bytecode.h"

#include <stdio.h>

static Result disassembleSimple(const char *name, uint8_t *code, size_t length,
                                size_t *index) {

    printf("%s\n", name);
    *index = *index + 1;
    return RESULT_OK;
}

#define DIS_UNARY(fName, type)                                                 \
    static Result disassemble##fName(const char *name, uint8_t *code,          \
                                     size_t length, size_t *index) {           \
                                                                               \
        if (*index >= length - sizeof(type)) {                                 \
                                                                               \
            return RESULT_ERR;                                                 \
        }                                                                      \
                                                                               \
        size_t paramIndex = *index + 1;                                        \
        type *paramPtr = (type *)(code + paramIndex);                          \
                                                                               \
        printf("%s\t\t%04d\n", name, *paramPtr);                               \
        *index = *index + 1 + sizeof(type);                                    \
                                                                               \
        return RESULT_OK;                                                      \
    }

DIS_UNARY(U8, uint8_t)
DIS_UNARY(U32, uint32_t)

#undef DIS_UNARY

static Result disassembleInstruction(uint8_t *code, size_t length,
                                     size_t *index) {

    printf("%04zu\t\t", *index);

    switch (code[*index]) {

#define SIMPLE(name)                                                           \
    case name: {                                                               \
        return disassembleSimple(#name, code, length, index);                  \
    } break;
#define U8(name)                                                               \
    case name: {                                                               \
        return disassembleU8(#name, code, length, index);                      \
    } break;
#define U32(name)                                                              \
    case name: {                                                               \
        return disassembleU32(#name, code, length, index);                     \
    } break;

        U8(OP_LOAD_CONST)
        SIMPLE(OP_TRUE)
        SIMPLE(OP_FALSE)
        SIMPLE(OP_NIL)

        U8(OP_DEFINE_GLOBAL)
        U8(OP_LOAD_GLOBAL)
        U8(OP_DEFINE_LOCAL)
        U8(OP_LOAD_LOCAL)

        SIMPLE(OP_INT)
        SIMPLE(OP_BOOL)
        SIMPLE(OP_NUM)
        SIMPLE(OP_STR)
        SIMPLE(OP_CLOCK)

        SIMPLE(OP_PRINT)
        SIMPLE(OP_PRINT_BLANK)
        SIMPLE(OP_RETURN)
        SIMPLE(OP_RETURN_VOID)
        SIMPLE(OP_POP)

        SIMPLE(OP_NEGATE)
        SIMPLE(OP_ADD)
        SIMPLE(OP_SUBTRACT)
        SIMPLE(OP_MULTIPLY)
        SIMPLE(OP_DIVIDE)

        SIMPLE(OP_LESS)
        SIMPLE(OP_NLESS)
        SIMPLE(OP_GREATER)
        SIMPLE(OP_NGREATER)
        SIMPLE(OP_EQUAL)
        SIMPLE(OP_NEQUAL)

        SIMPLE(OP_NOT)

        SIMPLE(OP_PUSH_SCOPE)
        SIMPLE(OP_POP_SCOPE)

        U32(OP_JUMP)
        U32(OP_JUMP_IF_NOT)
        U32(OP_LOOP)

        U8(OP_LOAD_PARAM)
        U32(OP_START_FUNCTION)
        U8(OP_CALL)

        U8(OP_CLOSURE)
        U8(OP_LOAD_UPVALUE)
        U8(OP_SET_UPVALUE)

        U8(OP_STRUCT)
        U8(OP_GET_FIELD)
        U8(OP_SET_FIELD)

#undef U32
#undef U8
#undef SIMPLE

        default: {

            printf("\n|| Unknown opcode %d\n", code[*index]);
            return RESULT_ERR;

        } break;
    }
}

Result disassembleCode(uint8_t *code, size_t length) {

    size_t index = 0;

    while (index < length) {

        if (disassembleInstruction(code, length, &index) != RESULT_OK) {

            return RESULT_ERR;
        }
    }

    return RESULT_OK;
}
