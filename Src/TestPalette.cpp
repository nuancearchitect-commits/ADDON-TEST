#include "TestPalette.hpp"

#include "DG.h"

#include "ResourceIds.hpp"
#include "TestMenu.hpp"
#include "TestSettings.hpp"

namespace {

	/* Remembers that the palette was visible before Archicad asked to hide it
	   (Hide All Palettes command, window change, project closing...). */
	bool wasVisibleBeforeHidden = false;

	GSFlags	PaletteControlFlags ()
	{
		return API_PalEnabled_FloorPlan + API_PalEnabled_Section + API_PalEnabled_Elevation +
			   API_PalEnabled_InteriorElevation + API_PalEnabled_3D + API_PalEnabled_Detail +
			   API_PalEnabled_Worksheet + API_PalEnabled_Layout + API_PalEnabled_DocumentFrom3D +
			   API_PalEnabled_ModelCompare;
	}

} /* anonymous namespace */

const GS::Guid& TESTPalette::PaletteGuid ()
{
	/* Fixed and unique identifier: the palette becomes dockable and the Work
	   Environment of Archicad can record the state of the palette. */
	static GS::Guid guid ("64388838-9390-4001-B741-A1DA91BFF66A");
	return guid;
}

Int32 TESTPalette::PaletteRefId ()
{
	static Int32 refId (GS::CalculateHashValue (PaletteGuid ()));
	return refId;
}

TESTPalette::TESTPalette () :
	DG::Palette (ACAPI_GetOwnResModule (), (short) ID_TEST_PALETTE, ACAPI_GetOwnResModule (), PaletteGuid ()),
	languageButton (GetReference (), (short) ID_TEST_PALETTE_BUTTON_ITEM)
{
	this->Attach (*this);
	AttachToAllItems (*this);

	this->BeginEventProcessing ();
}

TESTPalette::~TESTPalette ()
{
	this->EndEventProcessing ();
	this->Detach (*this);
	DetachFromAllItems (*this);
}

TESTPalette& TESTPalette::GetInstance ()
{
	static TESTPalette instance;
	return instance;
}

GSErrCode TESTPalette::Register ()
{
	return ACAPI_RegisterModelessWindow (PaletteRefId (), TESTPalette::PaletteAPIControlCallBack,
										 PaletteControlFlags (), GSGuid2APIGuid (PaletteGuid ()));
}

void TESTPalette::Unregister ()
{
	ACAPI_UnregisterModelessWindow (PaletteRefId ());
}

void TESTPalette::ShowPalette ()
{
	TESTPalette& palette = GetInstance ();
	palette.ApplyLanguage ();
	palette.Show ();
	palette.Activate ();
}

void TESTPalette::HidePalette ()
{
	TESTPalette& palette = GetInstance ();
	if (palette.IsVisible ())
		palette.Hide ();
}

void TESTPalette::TogglePalette ()
{
	TESTPalette& palette = GetInstance ();
	if (palette.IsVisible ()) {
		palette.Hide ();
	} else {
		palette.ApplyLanguage ();
		palette.Show ();
		palette.Activate ();
	}
}

void TESTPalette::ApplyLanguage ()
{
	const Int32			firstIndex	= TestSettings::GetFirstStringIndex ();
	const GSResModule		resModule	= ACAPI_GetOwnResModule ();
	const GS::UniString		titleText	= RSGetIndString (ID_TEST_STRINGS, firstIndex + (ID_TEST_STR_TITLE  - ID_TEST_STR_FIRST), resModule);
	const GS::UniString		infoText	= RSGetIndString (ID_TEST_STRINGS, firstIndex + (ID_TEST_STR_INFO   - ID_TEST_STR_FIRST), resModule);
	const GS::UniString		buttonText	= RSGetIndString (ID_TEST_STRINGS, firstIndex + (ID_TEST_STR_BUTTON - ID_TEST_STR_FIRST), resModule);

	const short dialogId = GetId ();

	DGSetDialogTitle (dialogId, titleText);
	DGSetItemText (dialogId, ID_TEST_PALETTE_INFO_ITEM, infoText);
	DGSetItemText (dialogId, ID_TEST_PALETTE_BUTTON_ITEM, buttonText);
}

void TESTPalette::PanelOpened (const DG::PanelOpenEvent& /*ev*/)
{
	ApplyLanguage ();
}

void TESTPalette::PanelCloseRequested (const DG::PanelCloseRequestEvent& /*ev*/, bool* /*accepted*/)
{
	/* A palette is never destroyed by the user, it is only hidden. */
	Hide ();
}

void TESTPalette::ButtonClicked (const DG::ButtonClickEvent& ev)
{
	if (ev.GetSource () == &languageButton) {
		TestSettings::ToggleLanguage ();
		ApplyLanguage ();
		TestMenu::UpdateMenuTexts ();
	}
}

GSErrCode TESTPalette::PaletteAPIControlCallBack (Int32 referenceID, API_PaletteMessageID messageID, GS::IntPtr param)
{
	if (referenceID != PaletteRefId ())
		return NoError;

	TESTPalette& palette = GetInstance ();

	switch (messageID) {
		case APIPalMsg_ClosePalette:
			palette.Hide ();
			break;

		case APIPalMsg_HidePalette_Begin:
			if (palette.IsVisible ()) {
				wasVisibleBeforeHidden = true;
				palette.Hide ();
			} else {
				wasVisibleBeforeHidden = false;
			}
			break;

		case APIPalMsg_OpenPalette:
			wasVisibleBeforeHidden = true;
			if (!palette.IsVisible ()) {
				palette.ApplyLanguage ();
				palette.Show ();
			}
			break;

		case APIPalMsg_HidePalette_End:
			if (wasVisibleBeforeHidden && !palette.IsVisible ()) {
				palette.ApplyLanguage ();
				palette.Show ();
			}
			wasVisibleBeforeHidden = false;
			break;

		case APIPalMsg_DisableItems_Begin:
			palette.DisableItems ();
			break;

		case APIPalMsg_DisableItems_End:
			palette.EnableItems ();
			break;

		case APIPalMsg_IsPaletteVisible:
			if (param != 0)
				*reinterpret_cast<bool*> (param) = palette.IsVisible ();
			break;

		default:
			break;
	}

	return NoError;
}
