
#include "bytecode.h"

#include <stdio.h>

static Result disassembleSimple(const char *name, uint8_t *code,
                                size_t *index) {

    printf("%s\n", name);
    (*index)++;
    return RESULT_OK;
}

static Result disassembleInstruction(uint8_t *code, size_t *index) {

    printf("%04zu\t\t", *index);

    switch (code[*index]) {

        case OP_TRUE: {

            return disassembleSimple("OP_TRUE", code, index);

        } break;

        default: {

            printf("\n");
            return RESULT_ERR;

        } break;
    }
}

Result disassembleCode(uint8_t *code, size_t length) {

    size_t index = 0;

    while (index < length) {

        if (disassembleInstruction(code, &index) != RESULT_OK) {

            return RESULT_ERR;
        }
    }

    return RESULT_OK;
}
