# Sets up an interface library for compiling with asan and ubsan.
# Also sets some env variables useful for adding to tests.
macro( setup_sanitizer_interface )

  if(BUILD_WITH_SANITIZERS)

    message(STATUS "Setting up compiler flags and runtime environment for ASAN")
    set(SANITIZER_COMPILER_FLAGS
      -fno-omit-frame-pointer
      -fno-sanitize-recover=undefined
      -fsanitize=address,undefined
      -fno-sanitize=vptr
    )
    set(SANITIZER_LINKER_FLAGS
      -fsanitize=address,undefined
    )

    set(commonOptions
      "verbosity=0"
      "halt_on_error=1"
      "symbolize=1"
      "color=never"
      "print_stacktrace=1"
    )

    set(asanOptions
      "report_globals=1"
      "check_initialization_order=1"
      "replace_str=1"
      "replace_intrin=1"
      "detect_stack_use_after_return=1"
      "strict_memcmp=1"
      "detect_leaks=1"
      "detect_odr_violation=1"
      "strict_string_checks=1"
      "detect_invalid_pointer_pairs=1"
    )

    set(lsanOptions
      "atexit=1"
    )

    set(ubsanOptions
      "integer-divide-by-zero=1"
      "float-cast-overflow=1"
      "implicit-conversion=1"
      "nonnull-attribute=1"
      "nullability-attribute=1"
      "pointer-overflow=1"
      "shift-base=1"
      "shift-exponent=1"
      "signed-integer-overflow=1"
      "unreachable=1"
    )

    list(JOIN commonOptions ":" TMP_COMMON)
    list(JOIN asanOptions ":" TMP_ASAN)
    list(JOIN lsanOptions ":" TMP_LSAN)
    list(JOIN ubsanOptions ":" TMP_UBSAN)

    set(XYCE_ASAN_OPTIONS "${TMP_COMMON}:${TMP_ASAN}")
    set(XYCE_LSAN_OPTIONS "${TMP_COMMON}:${TMP_LSAN}")
    set(XYCE_UBSAN_OPTIONS "${TMP_COMMON}:${TMP_UBSAN}")

  endif()

  # for cmake invoke the following as well. note this always needs to be executed
  # to set up the appropriate interface even though it will be empty when
  # not performing a sanitized build.
  if(${ARGC} EQUAL 0)

    message(STATUS "Setting up sanitizer interface")
    add_library(sanitizers INTERFACE)
    
    target_compile_options(sanitizers INTERFACE
      $<$<AND:$<CXX_COMPILER_ID:Clang,GNU>,$<BOOL:${BUILD_WITH_SANITIZERS}>>:${SANITIZER_COMPILER_FLAGS}>
    )
    target_link_options(sanitizers INTERFACE
      $<$<AND:$<CXX_COMPILER_ID:Clang,GNU>,$<BOOL:${BUILD_WITH_SANITIZERS}>>:${SANITIZER_LINKER_FLAGS}>
    )
  endif()
endmacro()
