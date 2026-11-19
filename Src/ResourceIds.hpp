#ifndef RESOURCEIDS_HPP
#define RESOURCEIDS_HPP

/* ---------------------------------------------------------------------------
 * Resource identifiers shared by the C++ sources and the GRC resources.
 *
 * This file is fed to the C preprocessor of Tools/CompileResources.py
 * (cl /EP on Windows, clang -E on macOS) before ResConv compiles a .grc.
 * Therefore it must contain preprocessor definitions ONLY - no C++ code.
 * (constexpr values declared in a C++ header are NOT visible to ResConv.)
 *
 * Archicad conventions (see "Modeless Palettes" in the Archicad C++ API doc):
 *   - palette dialog resource ids : 32400 - 32499
 *   - modal/modeless dialog ids   : 32500 - 32767
 *   - the 'MDID' resource MUST have the id 32500
 * ------------------------------------------------------------------------- */

/* --- localized resources: present once per language folder (RINT/, RFRA/) --- */
#define ID_TEST_INFO				32000	/* 'STR#' [1] add-on name, [2] add-on description */
#define ID_TEST_MENU				32500	/* 'STR#' [1] menu item text ('MDID' shares the same number, other type) */

/* --- language independent resources: RFIX/ (always compiled, both languages) --- */
#define ID_TEST_PALETTE				32400	/* 'GDLG' + 'DLGH' of the modeless palette */
#define ID_TEST_STRINGS				32530	/* 'STR#' bilingual UI strings (EN 1-4, FR 5-8) */

/* --- offsets inside 'STR#' ID_TEST_STRINGS --- */
#define ID_TEST_STR_FIRST			1
#define ID_TEST_STR_TITLE			1
#define ID_TEST_STR_INFO			2
#define ID_TEST_STR_BUTTON			3
#define ID_TEST_STR_MENU			4
#define ID_TEST_STR_LANG_COUNT		4		/* number of strings per language */

/* --- item indexes inside 'GDLG' ID_TEST_PALETTE (see RFIX/TestPalette.grc) --- */
#define ID_TEST_PALETTE_INFO_ITEM	1
#define ID_TEST_PALETTE_SEPARATOR	2
#define ID_TEST_PALETTE_BUTTON_ITEM	3

/* --- 'GICN' icon resource (RFIX/AddOnFix.grc + RFIX/Images/) --- */
#define ID_TEST_ICON				10001

#endif /* RESOURCEIDS_HPP */
