
#include "value.h"

#include "memory.h"

void initValueList(ValueList *list) {

    list->data = NULL;
    list->count = 0;
    list->capacity = 0;
}

void growValueList(ValueList *list) {

    size_t oldCapacity = list->capacity;
    list->capacity = GROW_CAPACITY(oldCapacity);
    list->data = GROW_ARRAY(list->data, Value, oldCapacity, list->capacity);
}

void appendValueList(ValueList *list, Value value) {

    if (list->capacity < list->count + 1) {

        growValueList(list);
    }

    list->data[list->count++] = value;
}

Result getValueList(ValueList *list, size_t index, Value *out) {

    if (index >= list->count) {

        return RESULT_ERR;
    }

    if (out != NULL) {

        *out = list->data[index];
    }

    return RESULT_OK;
}

Result setValueList(ValueList *list, size_t index, Value value) {

    if (index >= list->count) {

        return RESULT_ERR;
    }

    list->data[index] = value;

    return RESULT_OK;
}

void freeValueList(ValueList *list) {

    FREE_ARRAY(Value, list->data, list->capacity);
}
