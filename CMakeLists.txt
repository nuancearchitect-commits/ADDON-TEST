cmake_minimum_required (VERSION 3.19)

# Official Graphisoft build tools (git submodule: GRAPHISOFT/archicad-addon-cmake-tools).
include (Tools/CMakeCommon.cmake)

set_property (GLOBAL PROPERTY USE_FOLDERS ON)
set (AC_API_DEVKIT_DIR "$ENV{AC_API_DEVKIT_DIR}" CACHE PATH "API DevKit directory.")

if (NOT DEFINED AC_VERSION)
    message (FATAL_ERROR "AC_VERSION is not set!")
endif ()

message (STATUS "Archicad Version: ${AC_VERSION}")
SetGlobalCompilerDefinitions (${AC_VERSION})

# addOnName, addOnDefaultLanguage, addOnVersion, addOnCompanyName,
# addOnCopyrightYear, addOnDescription, addOnLanguages come from config.json.
ReadConfigJson ()
set (AC_ADDON_LANGUAGE "${addOnDefaultLanguage}" CACHE STRING "Add-On language code.")

project (${addOnName}-${AC_VERSION})

# Overridden by Tools/BuildAddOn.py with --forDistribution (-r) for release builds.
set (AC_ADDON_FOR_DISTRIBUTION OFF CACHE BOOL "")

set (AddOnSourcesFolder Src)
set (AddOnResourcesFolder .)

set (PCH_HEADER "Src/AddOnPrecompiledHeader.hpp")

GenerateAddOnProject (CMakeTarget ${AC_VERSION} "${AC_API_DEVKIT_DIR}" ${AddOnSourcesFolder} ${AddOnResourcesFolder} ${AC_ADDON_LANGUAGE} ${addOnDefaultLanguage} ${PCH_HEADER})
