#include "TestMenu.hpp"

#include "ResourceIds.hpp"
#include "TestPalette.hpp"
#include "TestSettings.hpp"

namespace {

	const Int32	PaletteToggleItemIndex = 1;

	/* Callback of the add-on menu command. */
	GSErrCode MenuCommandHandler (const API_MenuParams* menuParams)
	{
		if (menuParams == nullptr)
			return NoError;

		switch (menuParams->menuItemRef.menuResID) {
			case ID_TEST_MENU:
				switch (menuParams->menuItemRef.itemIndex) {
					case PaletteToggleItemIndex:
						TESTPalette::TogglePalette ();
						break;
					default:
						break;
				}
				break;
			default:
				break;
		}

		return NoError;
	}

} /* anonymous namespace */

namespace TestMenu {

	GSErrCode	RegisterMenu ()
	{
		/* The menu strings are taken from the 'STR#' resource of the language
		   the add-on was built with; UpdateMenuTexts () overrides them with the
		   strings of the language chosen by the user. */
		return ACAPI_MenuItem_RegisterMenu (ID_TEST_MENU, 0, MenuCode_Extras, MenuFlag_Default);
	}

	GSErrCode	InstallMenuHandler ()
	{
		return ACAPI_MenuItem_InstallMenuHandler (ID_TEST_MENU, MenuCommandHandler);
	}

	void	UpdateMenuTexts ()
	{
		const Int32			firstIndex = TestSettings::GetFirstStringIndex ();
		const Int32			stringIndex = firstIndex + (ID_TEST_STR_MENU - ID_TEST_STR_FIRST);
		GS::UniString		menuText = RSGetIndString (ID_TEST_STRINGS, stringIndex, ACAPI_GetOwnResModule ());

		API_MenuItemRef	menuItemRef = {};
		menuItemRef.menuResID	= (short) ID_TEST_MENU;
		menuItemRef.itemIndex	= PaletteToggleItemIndex;

		ACAPI_MenuItem_SetMenuItemText (&menuItemRef, nullptr, &menuText);
	}

} /* namespace TestMenu */
