cmake_minimum_required(VERSION 3.13...3.19)
project(HDF5_build LANGUAGES C Fortran)

include(${PROJECT_SOURCE_DIR}/../cmake/libraries.cmake)

include(ExternalProject)

if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)

  if(CMAKE_Fortran_COMPILER_ID STREQUAL GNU)
    set(prefix ~/lib_gcc)
  elseif(CMAKE_Fortran_COMPILER_ID STREQUAL Intel)
    set(prefix ~/lib_intel)
  elseif(CMAKE_Fortran_COMPILER_ID STREQUAL IntelLLVM)
    set(prefix ~/lib_intel)
  else()
    set(prefix ~/lib)
  endif()

  get_filename_component(prefix ${prefix} ABSOLUTE)
  set(CMAKE_INSTALL_PREFIX ${prefix} CACHE PATH "top-level install path" FORCE)
endif()

set(ZLIB_ROOT ${CMAKE_INSTALL_PREFIX}/zlib)
set(HDF5_ROOT ${CMAKE_INSTALL_PREFIX}/hdf5)

message(STATUS "Building and installing HDF5 to ${HDF5_ROOT}")

include(${PROJECT_SOURCE_DIR}/../cmake/build_hdf5.cmake)