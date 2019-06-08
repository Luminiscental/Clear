
#include "bytecode.h"

#include "memory.h"
#include <stdio.h>
#include <string.h>

static Result disassembleSimple(const char *name, size_t *index) {

    printf("%s\n", name);
    *index = *index + 1;
    return RESULT_OK;
}

#define DIS_UNARY(fName, format, type)                                         \
    static Result disassemble##fName(const char *name, uint8_t *code,          \
                                     size_t length, size_t *index) {           \
                                                                               \
        if (*index >= length - sizeof(type)) {                                 \
                                                                               \
            printf("\n");                                                      \
            return RESULT_ERR;                                                 \
        }                                                                      \
                                                                               \
        *index = *index + 1;                                                   \
        type *paramPtr = (type *)(code + *index);                              \
        *index = *index + sizeof(type);                                        \
                                                                               \
        printf("%-18s " format "\n", name, *paramPtr);                         \
                                                                               \
        return RESULT_OK;                                                      \
    }

DIS_UNARY(U8, "%d", uint8_t)
DIS_UNARY(U32, "%d", uint32_t)
DIS_UNARY(S32, "'%d'", int32_t)
DIS_UNARY(F64, "'%f'", double)

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

    size_t constantCount = *(uint32_t *)code;
    index = index + sizeof(uint32_t);

    for (size_t i = 0; i < constantCount; i++) {

        printf("%04zu ", index);

        switch (code[index]) {

            case OP_INTEGER: {

                if (disassembleS32("OP_INTEGER", code, length, &index) !=
                    RESULT_OK) {

                    return RESULT_ERR;
                }

            } break;

            case OP_NUMBER: {

                if (disassembleF64("OP_NUMBER", code, length, &index) !=
                    RESULT_OK) {

                    return RESULT_ERR;
                }

            } break;

            case OP_STRING: {

                printf("%-18s ", "OP_STRING");
                index++;

                if (index >= length - sizeof(uint8_t)) {

                    printf("\n");
                    return RESULT_ERR;
                }

                uint8_t strLength = *(uint8_t *)(code + index);
                index += sizeof(uint8_t);

                if (index >= length - strLength) {

                    printf("\n");
                    return RESULT_ERR;
                }

                char *str = ALLOCATE_ARRAY(char, strLength + 1);
                str[strLength] = '\0';

                memcpy(str, code + index, strLength);
                index += strLength;

                printf("'%s'\n", str);

            } break;

            default: {

                printf("\n|| Unknown constant type %d\n", code[index]);
                return RESULT_ERR;

            } break;
        }
    }

    while (index < length) {

        if (disassembleInstruction(code, length, &index) != RESULT_OK) {

            return RESULT_ERR;
        }
    }

    return RESULT_OK;
}
