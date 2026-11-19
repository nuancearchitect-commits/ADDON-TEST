/* TEST - a bilingual (French / English) empty palette for Archicad.
 *
 * Only functions documented by the Archicad API Development Kit are used here;
 * see Tools/README references in the repository README.md.
 */

#include "APIEnvir.h"
#include "ACAPinc.h"

#include "ResourceIds.hpp"
#include "TestMenu.hpp"
#include "TestPalette.hpp"

/* ---------------------------------------------------------------------------
 * Required functions of an Archicad add-on.
 * ------------------------------------------------------------------------- */

API_AddonType CheckEnvironment (API_EnvirParams* envir)
{
	/* Name and description shown in Options > Add-Ons.
	   These two strings are read from the resource folder of the language the
	   .apx was built with (RINT/ by default, RFRA/ for a French build). */
	RSGetIndString (&envir->addOnInfo.name,			ID_TEST_INFO, 1, ACAPI_GetOwnResModule ());
	RSGetIndString (&envir->addOnInfo.description,	ID_TEST_INFO, 2, ACAPI_GetOwnResModule ());

	return APIAddon_Normal;
}

GSErrCode RegisterInterface (void)
{
	return TestMenu::RegisterMenu ();
}

GSErrCode Initialize (void)
{
	GSErrCode err = TestMenu::InstallMenuHandler ();

	/* Registering the palette keeps the add-on in memory while Archicad runs,
	   and lets the API ask for show/hide and enable/disable actions. */
	TESTPalette::Register ();

	/* Apply the language the user selected before (stored in the preferences
	   of the add-on). */
	TestMenu::UpdateMenuTexts ();

	return err;
}

GSErrCode FreeData (void)
{
	TESTPalette::Unregister ();

	return NoError;
}
