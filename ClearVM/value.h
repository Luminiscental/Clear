#ifndef clearvm_value_h
#define clearvm_value_h

#include "common.h"

typedef enum eObjType ObjType;
typedef struct sObj Obj;
typedef struct sObjString ObjString;

typedef enum {

    VAL_NUMBER,
    VAL_BOOL,
    VAL_OBJ

} ValueType;

typedef struct {

    ValueType type;

    union {

        bool boolean;
        double number;
        Obj *obj;

    } as;

} Value;

Value makeBoolean(bool boolean);
Value makeNumber(double number);
Value makeString(size_t length, char *string);
bool valuesEqual(Value a, Value b);

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
