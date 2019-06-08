#ifndef clearvm_vm_h
#define clearvm_vm_h

#include "common.h"

typedef struct {

} VM;

void initVM(VM *vm);
void executeCode(VM *vm, unsigned char *code, size_t length);
void freeVM(VM *vm);

#endif
