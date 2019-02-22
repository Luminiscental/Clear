#ifndef clearvm_value_h
#define clearvm_value_h

#include "common.h"

typedef double Value;

typedef struct {

    size_t capacity;
    size_t count;
    Value *values;

} ValueArray;

void initValueArray(ValueArray *array);
void writeValueArray(ValueArray *array, Value value);
void freeValueArray(ValueArray *array);

void printValue(Value value, bool endLine);

#endif
