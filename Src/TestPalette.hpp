#ifndef TESTPALETTE_HPP
#define TESTPALETTE_HPP

#include "APIEnvir.h"
#include "ACAPinc.h"

#include "DGModule.hpp"

/* ---------------------------------------------------------------------------
 * The modeless palette of the TEST add-on.
 *
 * It is a "starting point" palette: it holds a single information line, a
 * separator and a button which switches the interface between French and
 * English. The palette is created from the language independent 'GDLG'
 * ID_TEST_PALETTE (see RFIX/TestPalette.grc); all of its texts are applied at
 * run time with DGSetDialogTitle () / DGSetItemText () from the bilingual
 * 'STR#' ID_TEST_STRINGS, so one single .apx serves both languages.
 *
 * Follows the official "Modeless Palettes" chapter of the Archicad C++ API:
 *   - 'GDLG' with the Palette window type, dialog id in the 32400-32499 range
 *   - DG::Palette to create the window, ACAPI_RegisterModelessWindow to let
 *     the API control it (show/hide with the other palettes, Work Environment)
 * ------------------------------------------------------------------------- */

class TESTPalette : public DG::Palette,
					public DG::PanelObserver,
					public DG::ButtonItemObserver,
					public DG::CompoundItemObserver
{
public:
	static TESTPalette&	GetInstance ();

	/* Called from Initialize / FreeData. */
	static GSErrCode	Register ();
	static void			Unregister ();

	/* Palette commands. */
	static void			ShowPalette ();
	static void			HidePalette ();
	static void			TogglePalette ();

	/* Identity of this palette for the Archicad API. */
	static Int32				PaletteRefId ();
	static const GS::Guid&		PaletteGuid ();

	/* Archicad asks the add-on to adapt the palette to its environment. */
	static GSErrCode	PaletteAPIControlCallBack (Int32 referenceID, API_PaletteMessageID messageID, GS::IntPtr param);

	/* Writes the strings of the selected language into the palette items. */
	void	ApplyLanguage ();

private:
	TESTPalette ();
	virtual	~TESTPalette ();

	virtual void	PanelOpened (const DG::PanelOpenEvent& ev) override;
	virtual void	PanelCloseRequested (const DG::PanelCloseRequestEvent& ev, bool* accepted) override;
	virtual void	ButtonClicked (const DG::ButtonClickEvent& ev) override;

	DG::Button	languageButton;
};

#endif /* TESTPALETTE_HPP */
