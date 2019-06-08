
#include "memory.h"

#include <stdio.h>
#include <stdlib.h>

void *reallocate(void *previous,
#ifdef DEBUG_MEM
                 size_t oldSize,
#endif
                 size_t newSize) {

#ifdef DEBUG_MEM

    static size_t memoryUsage = 0;

    memoryUsage += newSize;
    memoryUsage -= oldSize;

    printf("\t\t\t\t\t\t\t\tmemory: %zuB\n", memoryUsage);

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

        default: {

            printf("|| Unknown object type %d could not be freed\n", obj->type);

        } break;
    }
}
