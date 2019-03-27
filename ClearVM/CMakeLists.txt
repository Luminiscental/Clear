cmake_minimum_required(VERSION 2.6.0)
project(clr C)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall")
# add_compile_definitions(DEBUG_FILE)
add_compile_definitions(DEBUG_DIS)
# add_compile_definitions(DEBUG_TRACE)
# add_compile_definitions(DEBUG_STACK)
# add_compile_definitions(DEBUG_MEM)

add_executable(clr main.c chunk.c memory.c vm.c value.c obj.c table.c)
target_link_libraries(clr m)
