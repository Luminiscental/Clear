#ifndef clearvm_vm_h
#define clearvm_vm_h

#include "bytecode.h"
#include "common.h"
#include "value.h"

typedef Result (*Instruction)(VM *vm);

#define GLOBAL_MAX 256

typedef struct {

    bool isSet[GLOBAL_MAX];
    Value data[GLOBAL_MAX];

} GlobalArray;

void initGlobalArray(GlobalArray *array);
Result getGlobal(GlobalArray *array, size_t index, Value *out);
Result setGlobal(GlobalArray *array, size_t index, Value in);

#define STACK_MAX 512

struct sVM {

    uint8_t *start; // points to the first byte of the code to execute
    uint8_t *end;   // points after the last byte of the code to execute

    uint8_t *ip; // instruction pointer; points to next instruction to execute
    Value *fp;   // frame pointer; points to first local in current frame
    Value *sp;   // stack pointer; points to next available value on stack

    Value stack[STACK_MAX]; // stack storage (array)

    GlobalArray globals; // global storage (array)

    ObjectValue *objects; // heap storage (linked list)

    Value *constants; // constant storage (array)
    size_t constantCount;

    Instruction instructions[OP_COUNT]; // Instruction function pointers
};

Result initVM(VM *vm);
Result executeCode(VM *vm, uint8_t *code, size_t length);
void freeVM(VM *vm);

#endif
