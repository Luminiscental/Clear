cmake_minimum_required(VERSION 2.6.0)
project(clr C)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall")
# add_compile_definitions(DEBUG)
# add_compile_definitions(DEBUG_MEM)

add_executable(clr main.c chunk.c memory.c vm.c value.c)
