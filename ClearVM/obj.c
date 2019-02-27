
#include "obj.h"

#include <stdlib.h>
#include <string.h>

Value concatStrings(ObjString *first, ObjString *second) {

    size_t newLength = first->length + second->length;

    char *result = (char*) malloc(newLength + 1);
    result[newLength] = '\0';

    strcpy(result, first->chars);
    strcat(result, second->chars);

    free(first->chars);
    free(second->chars);

    free(first);
    free(second);

    return makeString(newLength, result);
}

bool stringsEqual(ObjString *a, ObjString *b) {

    if (a->length != b->length) return false;

    return memcmp(a->chars, b->chars, a->length) == 0;
}

bool isObjType(Value a, ObjType type) {

    return a.type == VAL_OBJ && a.as.obj->type == type;
}

