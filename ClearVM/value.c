
#include "value.h"

#include <stdio.h>
#include <stdlib.h>

#include "memory.h"

Value makeNumber(double number) {

    Value result;

    result.type = VAL_NUMBER;
    result.as.number = number;

    return result;
}

Value makeString(char *string) {

    Value result;

    result.type = VAL_STRING;
    result.as.string = string;

    return result;
}

void initValueArray(ValueArray *array) {

    array->values = NULL;
    array->capacity = 0;
    array->count = 0;
}

void writeValueArray(ValueArray *array, Value value) {

    if (array->capacity < array->count + 1) {

        int oldCapacity = array->capacity;
        array->capacity = GROW_CAPACITY(oldCapacity);
        array->values = GROW_ARRAY(array->values, Value, oldCapacity,
                array->capacity);
    }

    array->values[array->count++] = value;
}

void freeValueArray(ValueArray *array) {

    for (size_t i = 0; i < array->count; i++) {

        Value value = array->values[i];

        if (value.type == VAL_STRING) {

            free(value.as.string);
        }
    }

    FREE_ARRAY(Value, array->values, array->capacity);
    initValueArray(array);
}

void printValue(Value value, bool endLine) {

    switch (value.type) {

        case VAL_NUMBER: {

            printf("<num %g>", value.as.number);

        } break;

        case VAL_STRING: {

            printf("<str \"%s\">", value.as.string);

        } break;
    }

    if (endLine) printf("\n");
}

