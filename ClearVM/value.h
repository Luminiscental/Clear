#ifndef clearvm_value_h
#define clearvm_value_h

#include "common.h"

typedef struct sVM VM;
typedef enum eObjType ObjType;
typedef struct sObj Obj;
typedef struct sObjString ObjString;

#define NUMBER_PRECISION 0.0000001
#define NUMBER_PLACES 7

typedef enum {

    VAL_NUMBER,
    VAL_INTEGER,
    VAL_BOOL,
    VAL_OBJ

} ValueType;

typedef struct {

    ValueType type;
    uint32_t hash;

    union {

        bool boolean;
        int32_t integer;
        double number;
        Obj *obj;

    } as;

} Value;

Value makeInteger(int32_t integer);
Value makeBoolean(bool boolean);
Value makeNumber(double number);
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
