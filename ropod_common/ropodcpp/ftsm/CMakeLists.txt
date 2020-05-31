cmake_minimum_required(VERSION 2.8)

find_package(PkgConfig)
include(FindPkgConfig)
pkg_check_modules(LIBMONGOCXX REQUIRED libmongocxx)
pkg_check_modules(LIBBSONCXX REQUIRED libbsoncxx)
pkg_check_modules(JSONCPP jsoncpp)

include_directories(
  /opt/ropod/ftsm/cppftsm/include
  /opt/ropod/ropod_common/ropodcpp/ftsm/include
  ${LIBMONGOCXX_INCLUDE_DIRS}
  ${LIBBSONCXX_INCLUDE_DIRS}
  ${JSONCPP_INCLUDE_DIRS}
)

link_directories(
  ${LIBMONGOCXX_LIBRARY_DIRS}
  ${LIBBSONCXX_LIBRARY_DIRS}
)

set(FTSM_LIBRARIES
  ${LIBMONGOCXX_LIBRARIES}
  ${LIBBSONCXX_LIBRARIES}
  ${JSONCPP_LIBRARIES}
)
