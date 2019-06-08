#ifndef clearvm_value_h
#define clearvm_value_h

#include "common.h"

typedef union {

    bool asBool;
    uint8_t asU8;
    uint32_t asU32;
    uint64_t asU64;
    int8_t asS8;
    int32_t asS32;
    int64_t asS64;
    void *asPtr;

} Value;

typedef struct {

    Value *data;
    size_t count;
    size_t capacity;

} ValueList;

void initValueList(ValueList *list);

void growValueList(ValueList *list);
void appendValueList(ValueList *list, Value value);
Result getValueList(ValueList *list, size_t index, Value *out);
Result setValueList(ValueList *list, size_t index, Value value);

void freeValueList(ValueList *list);

#endif
