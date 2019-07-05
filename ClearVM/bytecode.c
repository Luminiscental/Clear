
#include "bytecode.h"

#include "memory.h"
#include <stdio.h>
#include <string.h>

static Result disassembleSimple(const char *name, size_t *index) {

    *index = *index + 1;

    printf("%s\n", name);

    return RESULT_OK;
}

#define DIS_UNARY(fName, format, type)                                         \
    static Result disassemble##fName(const char *name, uint8_t *code,          \
                                     size_t length, size_t *index) {           \
                                                                               \
        *index = *index + 1;                                                   \
        if (*index > length - sizeof(type)) {                                  \
                                                                               \
            printf("\n|| EOF reached while parsing constant " #type "\n");     \
            return RESULT_ERR;                                                 \
        }                                                                      \
                                                                               \
        type *paramPtr = (type *)(code + *index);                              \
        *index = *index + sizeof(type);                                        \
                                                                               \
        printf("%-18s " format "\n", name, *paramPtr);                         \
                                                                               \
        return RESULT_OK;                                                      \
    }

#define DIS_BINARY(fName, format1, type1, format2, type2)                      \
    static Result disassemble##fName(const char *name, uint8_t *code,          \
                                     size_t length, size_t *index) {           \
                                                                               \
        *index = *index + 1;                                                   \
        if (*index > length - sizeof(type1) - sizeof(type2)) {                 \
                                                                               \
            printf("\n|| EOF reached while parsing " #type1 ", " #type2        \
                   " arguments\n");                                            \
            return RESULT_ERR;                                                 \
        }                                                                      \
                                                                               \
        type1 *arg1Ptr = (type1 *)(code + *index);                             \
        *index += sizeof(type1);                                               \
                                                                               \
        type2 *arg2Ptr = (type2 *)(code + *index);                             \
        *index += sizeof(type2);                                               \
                                                                               \
        printf("%-18s " format1 " " format2 "\n", name, *arg1Ptr, *arg2Ptr);   \
                                                                               \
        return RESULT_OK;                                                      \
    }

DIS_UNARY(U8, "%d", uint8_t)
DIS_UNARY(S32, "'%d'", int32_t)
DIS_UNARY(F64, "'%f'", double)
DIS_BINARY(U8U8, "%d", uint8_t, "%d", uint8_t)

#undef DIS_BINARY
#undef DIS_UNARY

static Result disassembleInstruction(uint8_t *code, size_t length,
                                     size_t *index) {

    printf("%04zu ", *index);

    switch (code[*index]) {

#define SIMPLE(name)                                                           \
    case name: {                                                               \
        return disassembleSimple(#name, index);                                \
    } break;
#define U8(name)                                                               \
    case name: {                                                               \
        return disassembleU8(#name, code, length, index);                      \
    } break;
#define U8U8(name)                                                             \
    case name: {                                                               \
        return disassembleU8U8(#name, code, length, index);                    \
    } break;

        U8(OP_PUSH_CONST)
        SIMPLE(OP_PUSH_TRUE)
        SIMPLE(OP_PUSH_FALSE)
        SIMPLE(OP_PUSH_NIL)

        U8(OP_SET_GLOBAL)
        U8(OP_PUSH_GLOBAL)
        U8(OP_SET_LOCAL)
        U8(OP_PUSH_LOCAL)

        SIMPLE(OP_INT)
        SIMPLE(OP_BOOL)
        SIMPLE(OP_NUM)
        SIMPLE(OP_STR)
        SIMPLE(OP_CLOCK)
        SIMPLE(OP_PRINT)

        SIMPLE(OP_POP)
        SIMPLE(OP_SQUASH)

        SIMPLE(OP_INT_NEG)
        SIMPLE(OP_NUM_NEG)
        SIMPLE(OP_INT_ADD)
        SIMPLE(OP_NUM_ADD)
        SIMPLE(OP_INT_SUB)
        SIMPLE(OP_NUM_SUB)
        SIMPLE(OP_INT_MUL)
        SIMPLE(OP_NUM_MUL)
        SIMPLE(OP_INT_DIV)
        SIMPLE(OP_NUM_DIV)
        SIMPLE(OP_STR_CAT)
        SIMPLE(OP_NOT)

        SIMPLE(OP_INT_LESS)
        SIMPLE(OP_NUM_LESS)
        SIMPLE(OP_INT_GREATER)
        SIMPLE(OP_NUM_GREATER)
        SIMPLE(OP_EQUAL)

        U8(OP_JUMP)
        U8(OP_JUMP_IF_FALSE)
        U8(OP_LOOP)

        U8(OP_FUNCTION)
        U8(OP_CALL)
        SIMPLE(OP_LOAD_IP)
        SIMPLE(OP_LOAD_FP)
        SIMPLE(OP_SET_RETURN)
        SIMPLE(OP_PUSH_RETURN)

        U8(OP_STRUCT)
        U8(OP_DESTRUCT)
        U8(OP_GET_FIELD)
        U8U8(OP_EXTRACT_FIELD)
        U8(OP_SET_FIELD)
        U8U8(OP_INSERT_FIELD)

        U8(OP_REF_LOCAL)
        SIMPLE(OP_DEREF)
        SIMPLE(OP_SET_REF)

        U8(OP_IS_VAL_TYPE)
        U8(OP_IS_OBJ_TYPE)

#undef U8U8
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

    size_t constantCount = *(uint8_t *)code;
    index = index + sizeof(uint8_t);

    for (size_t i = 0; i < constantCount; i++) {

        printf("%04zu ", index);

        switch (code[index]) {

            case CONST_INT: {

                if (disassembleS32("CONST_INT", code, length, &index) !=
                    RESULT_OK) {

                    return RESULT_ERR;
                }

            } break;

            case CONST_NUM: {

                if (disassembleF64("CONST_NUM", code, length, &index) !=
                    RESULT_OK) {

                    return RESULT_ERR;
                }

            } break;

            case CONST_STR: {

                printf("%-18s ", "CONST_STR");
                index++;

                if (index > length - sizeof(uint8_t)) {

                    printf(
                        "\n|| EOF reached instead of constant string length\n");
                    return RESULT_ERR;
                }

                uint8_t strLength = *(uint8_t *)(code + index);
                index += sizeof(uint8_t);

                if (index > length - strLength) {

                    printf("\n|| Reached EOF while parsing constant string\n");
                    return RESULT_ERR;
                }

                printf("'%.*s'\n", strLength, code + index);
                index += strLength;

            } break;

            default: {

                printf("\n|| Unknown constant type %d\n", code[index]);
                return RESULT_ERR;

            } break;
        }
    }

    while (index < length) {

        if (disassembleInstruction(code, length, &index) != RESULT_OK) {

            printf("|| Instruction at index %zu was invalid\n", index);
            return RESULT_ERR;
        }
    }

    return RESULT_OK;
}
