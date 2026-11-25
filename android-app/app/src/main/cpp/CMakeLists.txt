cmake_minimum_required(VERSION 3.22.1)
project(shai_local LANGUAGES C CXX)
# Optimise inference even in the installable debug research APK; retain symbols.
set(CMAKE_C_FLAGS_DEBUG "-O3 -g" CACHE STRING "Optimised native debug C" FORCE)
set(CMAKE_CXX_FLAGS_DEBUG "-O3 -g" CACHE STRING "Optimised native debug C++" FORCE)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
include(FetchContent)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "")
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(GGML_NATIVE OFF CACHE BOOL "")
set(GGML_CPU_ARM_ARCH "armv8-a" CACHE STRING "")
set(GGML_OPENMP OFF CACHE BOOL "")
set(LLAMA_BUILD_COMMON OFF CACHE BOOL "")
set(LLAMA_CURL OFF CACHE BOOL "")
FetchContent_Declare(llama_src
    URL https://codeload.github.com/ggml-org/llama.cpp/tar.gz/74d4f5b041ad837153b0e90fc864b8290e01d8d5
    URL_HASH SHA256=8dd9fcc7c17f972673960ffdcc7521f52de5a9ec594aa6acebd9dfd8c17c0a5c)
FetchContent_MakeAvailable(llama_src)
# This pinned GGUF reader reports parse/open failures to stderr, bypassing
# llama_log_set. Route only its errors to the existing bounded load logger.
# No process-wide stderr redirection and no prompt/response logging.
set(SHAI_GGUF_SOURCE "${llama_src_SOURCE_DIR}/ggml/src/gguf.cpp")
file(READ "${SHAI_GGUF_SOURCE}" SHAI_GGUF_TEXT)
string(REPLACE "fprintf(stderr, " "GGML_LOG_ERROR(" SHAI_GGUF_PATCHED "${SHAI_GGUF_TEXT}")
if(NOT SHAI_GGUF_PATCHED STREQUAL SHAI_GGUF_TEXT)
    file(WRITE "${SHAI_GGUF_SOURCE}" "${SHAI_GGUF_PATCHED}")
endif()
add_library(shai_local SHARED chat.cpp)
target_compile_features(shai_local PRIVATE cxx_std_17)
target_link_libraries(shai_local PRIVATE llama)
