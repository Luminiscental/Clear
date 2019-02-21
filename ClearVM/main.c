
#include <stdio.h>
#include <stdlib.h>

typedef struct {

    char *buffer;
    long length;

} FileBuffer;

FileBuffer readFile(const char *fileName) {

    FILE *inFile = fopen(fileName, "rb");

    FileBuffer result = { .buffer = NULL, .length = 0 };

    if (!inFile) {

        return result;
    }

    if (fseek(inFile, 0, SEEK_END)) {
        
        fclose(inFile);
        return result;
    }

    long fileLength = ftell(inFile);

    if (fseek(inFile, 0, SEEK_SET)) {

        fclose(inFile);
        return result;
    }

    char *buffer = (char*) malloc(fileLength);

    fread(buffer, 1, fileLength, inFile);

    fclose(inFile);

    result.buffer = buffer;
    result.length = fileLength;

    return result;
}

void run(FileBuffer byteCode) {

    for (long i = 0; i < byteCode.length; i++) {

        char byte = byteCode.buffer[i];
        printf("%d\n", byte);
    }
}

int main(int argc, char **argv) {

    if (argc < 2) {

        printf("Incorrect usage: Please pass a .crb file to run\n");
        return 1;
    }

    FileBuffer byteCode = readFile(argv[1]);

    if (byteCode.buffer == NULL) {

        printf("Could not read file!\n");
    }

    run(byteCode);

    free(byteCode.buffer);

    return 0;
}

