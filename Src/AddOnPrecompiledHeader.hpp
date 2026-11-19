#ifndef TEST_ADDON_PRECOMPILED_HEADER_HPP
#define TEST_ADDON_PRECOMPILED_HEADER_HPP

/* Precompiled header given to GenerateAddOnProject (see CMakeLists.txt).
 * <GSNew.hpp> and <GSMalloc.hpp> must stay the first includes, so that the
 * Graphisoft custom allocators are used consistently in the add-on. */

#include <GSNew.hpp>
#include <GSMalloc.hpp>

#if defined (macintosh)
namespace std {
	void *GS_realloc (void *userData, size_t newSize);
}
#endif

#include <limits.h>
#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <vector>
#include <memory>

#if defined (WINDOWS)
#include "Win32Interface.hpp"
#endif

#include "APIEnvir.h"
#include "ACAPinc.h"

#endif // TEST_ADDON_PRECOMPILED_HEADER_HPP
