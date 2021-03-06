add_executable(test_minimal test_minimal.f90)
# even though we're not using h5fortran, we're testing that HDF5 was linked
# as part of h5fortran
target_link_libraries(test_minimal PRIVATE h5fortran::h5fortran)
set_target_properties(test_minimal PROPERTIES LABELS unit)
add_test(NAME h5fortran:minimal
  COMMAND $<TARGET_FILE:test_minimal>)
set_tests_properties(h5fortran:minimal PROPERTIES
  FIXTURES_SETUP h5lib
  TIMEOUT 5
  LABELS core)

function(setup_test names)

set(CI $ENV{CI})

foreach(name IN LISTS names)

if(${name} MATCHES ".*fail.*")
  if(CI)
    continue()
  elseif(NOT test_shaky)
    continue()
  endif()
endif()

add_executable(test_${name} test_${name}.f90)
target_link_libraries(test_${name} PRIVATE h5fortran::h5fortran)
if(${CMAKE_Fortran_COMPILER_ID} STREQUAL GNU)
  target_compile_options(test_${name} PRIVATE -Wno-compare-reals -Wno-conversion)
endif()
set_target_properties(test_${name} PROPERTIES LABELS unit)

add_test(NAME h5fortran:${name}
  COMMAND $<TARGET_FILE:test_${name}>)
set_tests_properties(h5fortran:${name} PROPERTIES
  FIXTURES_REQUIRED h5lib
  TIMEOUT 10)


if(${name} MATCHES ".*fail.*")
  set_tests_properties(h5fortran:${name} PROPERTIES
    WILL_FAIL true
    LABELS shaky)
else()
  set_tests_properties(h5fortran:${name} PROPERTIES
    LABELS unit)
endif()

endforeach()

endfunction(setup_test)

# --- all other tests
set(testnames array attributes deflate error exist module layout lt scalar shape string
fail_read_size_mismatch fail_read_rank_mismatch fail_nonexist_variable)

if(f08block)
  list(APPEND testnames destructor)
else()
  message(STATUS "SKIP: destructor test since compiler can't do F2008 block")
endif()

setup_test("${testnames}")

set(shape_file ${CMAKE_CURRENT_BINARY_DIR}/test_shape.h5)
# --- Python h5py

find_package(Python3 COMPONENTS Interpreter)
if(NOT DEFINED h5py_ok)
  execute_process(COMMAND ${Python3_EXECUTABLE} -c "import h5py"
    RESULT_VARIABLE h5py_code
    TIMEOUT 15)
  if(h5py_code EQUAL 0)
    set(h5py_ok true CACHE BOOL "h5py OK")
  else()
    set(h5py_ok false CACHE BOOL "h5py not OK")
  endif()
endif()

if(h5py_ok)
  add_test(NAME h5fortran:PythonShape
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/test_shape.py ${shape_file})

    set_tests_properties(h5fortran:PythonShape PROPERTIES
    DEPENDS h5fortran:shape
    REQUIRED_FILES ${shape_file}
    FIXTURES_REQUIRED h5lib
    TIMEOUT 15)
endif(h5py_ok)

# --- Matlab HDF5

if(matlab)
find_package(Matlab COMPONENTS MAIN_PROGRAM)
if(Matlab_FOUND)
  set(matlab_cmd "i=h5info('${shape_file}', '/d7').Dataspace.Size; assert(all(i == [2, 1, 3, 4, 7, 6, 5]))")

  add_test(NAME h5fortran:MatlabShape COMMAND ${Matlab_MAIN_PROGRAM} -batch ${matlab_cmd})

  set_tests_properties(h5fortran:MatlabShape PROPERTIES
    TIMEOUT 90
    LABELS shaky
    DEPENDS h5fortran:shape
    REQUIRED_FILES ${shape_file}
    FIXTURES_REQUIRED h5lib)

endif(Matlab_FOUND)
endif(matlab)

# --- h5ls

find_program(h5ls NAMES h5ls)
if(h5ls)
  add_test(NAME h5fortran:h5ls COMMAND ${h5ls} ${shape_file}/d7)

  set_tests_properties(h5fortran:h5ls PROPERTIES
   TIMEOUT 10
   REQUIRED_FILES ${shape_file}
   FIXTURES_REQUIRED h5lib
   DEPENDS h5fortran:shape
   PASS_REGULAR_EXPRESSION "{5, 6, 7, 4, 3, 1, 2}")

endif(h5ls)
