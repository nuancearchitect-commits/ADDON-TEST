#ifndef TESTMENU_HPP
#define TESTMENU_HPP

#include "ACAPinc.h"

/* Menu integration of the add-on. The menu command toggles the palette. */

namespace TestMenu {

	/* Called from RegisterInterface: mounts the menu command. */
	GSErrCode	RegisterMenu ();

	/* Called from Initialize and after a language change: installs the command
	   handler and applies the localized menu text of the current language. */
	GSErrCode	InstallMenuHandler ();

	/* Sets the menu item text (and the Work Environment text) according to the
	   currently selected language. */
	void		UpdateMenuTexts ();

} /* namespace TestMenu */

#endif /* TESTMENU_HPP */
