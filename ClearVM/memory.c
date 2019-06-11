
#include "memory.h"

#include <stdio.h>
#include <stdlib.h>

void *reallocate(void *previous, size_t oldSize, size_t newSize) {

#ifdef DEBUG_MEM

    static size_t memoryUsage = 0;

    memoryUsage += newSize;
    memoryUsage -= oldSize;

    printf("\t\t\t\t\t\t\t\tmemory: %zuB\n", memoryUsage);

#else

    UNUSED(oldSize);

#endif

    if (newSize == 0) {

        free(previous);
        return NULL;
    }

    return realloc(previous, newSize);
}

void freeObject(ObjectValue *obj) {

    switch (obj->type) {

        case OBJ_STRING: {

            StringObject *strObj = (StringObject *)obj->ptr;
            FREE_ARRAY(char, strObj->data, strObj->length + 1);
            FREE(StringObject, strObj);

        } break;

        case OBJ_STRUCT: {

            StructObject *structObj = (StructObject *)obj->ptr;
            FREE_ARRAY(Value, structObj->fields, structObj->fieldCount);
            FREE(StructObject, structObj);

        } break;

        case OBJ_UPVALUE: {

            UpvalueObject *upvalueObj = (UpvalueObject *)obj->ptr;
            FREE(UpvalueObject, upvalueObj);

        } break;

        default: {

            printf("|| Unknown object type %d could not be freed\n", obj->type);

        } break;
    }

    FREE(ObjectValue, obj);
}
