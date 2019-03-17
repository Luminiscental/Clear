
#include "obj.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "memory.h"
#include "table.h"
#include "vm.h"

#define ALLOCATE_OBJ(vm, type, objType)                                        \
    (type *)allocateObject(vm, sizeof(type), objType)

static Obj *allocateObject(VM *vm, size_t size, ObjType type) {

    Obj *obj = (Obj *)reallocate(NULL, 0, size);

    obj->type = type;
    obj->next = vm->objects;
    vm->objects = obj;

    return obj;
}

static ObjString *allocateString(VM *vm, size_t length, char *string) {

    ObjString *objStr = ALLOCATE_OBJ(vm, ObjString, OBJ_STRING);

    objStr->chars = string;
    objStr->length = length;

    return objStr;
}

static uint32_t hashChars(size_t length, const char *chars) {

    uint32_t hash = 2166136261u;

    for (size_t i = 0; i < length; i++) {

        hash ^= chars[i];
        hash *= 16777619;
    }

    return hash;
}

static Entry *tableFindString(Table *table, const char *string, size_t length) {

    if (table->entries == NULL)
        return NULL;

    uint32_t hash = hashChars(length, string);
    uint32_t index = hash % table->capacity;

    while (true) {

        Entry *entry = table->entries + index;

        if (entry->state == ENTRY_EMPTY) {

            return NULL;

        } else if (entry->state == ENTRY_FULL) {

            ObjString *entryStr = (ObjString *)entry->key.as.obj;

            if (entryStr->length == length && entry->key.hash == hash &&
                memcmp(entryStr->chars, string, length) == 0) {

                return entry;
            }
        }

        index = (index + 1) % table->capacity;
    }
}

Value makeStringFromLiteral(VM *vm, const char *string) {

    size_t length = strlen(string);
    Entry *interned = tableFindString(&vm->strings, string, length);

    if (interned != NULL) {

        return interned->key;
    }

    Value result;

    char *copyStr = ALLOCATE(char, length + 1);
    strcpy(copyStr, string);

    ObjString *stringObj = allocateString(vm, length, copyStr);

    result.type = VAL_OBJ;
    result.hash = hashChars(length, string);

    result.as.obj = (Obj *)stringObj;

    stringObj->chars = copyStr;
    stringObj->length = length;

    tableSet(&vm->strings, result, makeBoolean(true));

    return result;
}

static size_t countDigits(int32_t integer) {

    size_t digits = 0;

    do {

        integer /= 10;
        digits++;

    } while (integer != 0);

    return digits;
}

Value makeStringFromInteger(VM *vm, int32_t integer) {

    size_t minusSignLength = (integer < 0) ? 1 : 0;
    size_t digits = countDigits(integer);
    size_t length = minusSignLength + digits;

    char *buffer = ALLOCATE(char, length + 1);
    buffer[length] = '\0';

    snprintf(buffer, length + 1, "%d", integer);

    return makeString(vm, digits, buffer);
}

char *makeRawStringFromNumber(double number, size_t *lengthOut) {

    size_t minusSignLength = (number < 0) ? 1 : 0;

    double size = (number < 0) ? -number : number;
    size_t preDecimalDigits = size < 1.0 ? 1 : 1 + (size_t)log10(size);
    size_t length = minusSignLength + preDecimalDigits + 1 + NUMBER_PLACES;

    char *buffer = ALLOCATE(char, length + 1);
    buffer[length] = '\0';

    snprintf(buffer, length + 1, "%.*f", NUMBER_PLACES, number);

    if (lengthOut != NULL) {

        *lengthOut = length;
    }

    return buffer;
}

Value makeStringFromNumber(VM *vm, double number) {

    size_t length;
    char *buffer = makeRawStringFromNumber(number, &length);

    return makeString(vm, length, buffer);
}

Value makeString(VM *vm, size_t length, char *string) {

    Entry *interned = tableFindString(&vm->strings, string, length);

    if (interned != NULL) {

        FREE_ARRAY(char, string, length + 1);
        return interned->key;
    }

    Value result;

    ObjString *stringObj = allocateString(vm, length, string);

    result.type = VAL_OBJ;
    result.hash = hashChars(length, string);

    result.as.obj = (Obj *)stringObj;

    stringObj->chars = string;
    stringObj->length = length;

    tableSet(&vm->strings, result, makeBoolean(true));

    return result;
}

Value concatStrings(VM *vm, ObjString *first, ObjString *second) {

    size_t newLength = first->length + second->length;

    char *result = ALLOCATE(char, newLength + 1);
    result[newLength] = '\0';

    strcpy(result, first->chars);
    strcat(result, second->chars);

    return makeString(vm, newLength, result);
}

Value makeFunction(VM *vm, uint8_t *code, size_t size) {

    ObjFunction *objFunc = ALLOCATE_OBJ(vm, ObjFunction, OBJ_FUNCTION);

    objFunc->code = code;
    objFunc->size = size;
    objFunc->ip = code;

    Value result;

    result.type = VAL_OBJ;
    result.hash = (size_t)objFunc;
    result.as.obj = (Obj *)objFunc;

    return result;
}
bool isObjType(Value a, ObjType type) {

    return a.type == VAL_OBJ && a.as.obj->type == type;
}
