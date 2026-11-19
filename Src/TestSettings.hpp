#ifndef TESTSETTINGS_HPP
#define TESTSETTINGS_HPP

#include "ACAPinc.h"

/* ---------------------------------------------------------------------------
 * Language state of the add-on.
 *
 * The .apx is bilingual: every string of the user interface is stored twice in
 * the language independent 'STR#' resource ID_TEST_STRINGS (see
 * RFIX/TestPalette.grc) - English first, French second. Which half is used is
 * decided here, and the choice is persisted in the Archicad preferences of this
 * add-on (ACAPI_GetPreferences / ACAPI_SetPreferences), so it survives restarts.
 * ------------------------------------------------------------------------- */

namespace TestSettings {

	enum Language {
		English = 0,
		French	= 1
	};

	/* Returns the selected language. The value is read from the preferences
	   the first time it is needed, and defaults to the language the .apx was
	   built for (AC_ADDON_LANGUAGE / ADDON_LANGUAGE). */
	Language	GetLanguage ();

	/* Sets and stores the language. */
	void		SetLanguage (Language language);

	/* English <-> French. */
	void		ToggleLanguage ();

	/* First index of ID_TEST_STRINGS belonging to the current language. */
	Int32		GetFirstStringIndex ();

} /* namespace TestSettings */

#endif /* TESTSETTINGS_HPP */
