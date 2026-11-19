#include "TestSettings.hpp"

#include <cstring>

#include "ResourceIds.hpp"

namespace {

	const Int32	TestSettingsVersion	= 1;
	const Int32	LanguageCount			= 2;

	TestSettings::Language	DefaultLanguage ()
	{
		/* ADDON_LANGUAGE is defined by the build system with the value of
		   AC_ADDON_LANGUAGE (see Tools/CMakeCommon.cmake): "INT" or "FRA". */
		return (std::strcmp (ADDON_LANGUAGE, "FRA") == 0) ? TestSettings::French : TestSettings::English;
	}

	bool	ReadLanguageFromPreferences (TestSettings::Language* language)
	{
		Int32	storedVersion	= 0;
		GSSize	storedBytes		= 0;

		if (ACAPI_GetPreferences (&storedVersion, &storedBytes, nullptr) != NoError)
			return false;
		if (storedVersion != TestSettingsVersion || storedBytes != (GSSize) sizeof (Int32))
			return false;

		Int32	storedLanguage = 0;
		if (ACAPI_GetPreferences (&storedVersion, &storedBytes, &storedLanguage) != NoError)
			return false;

		const bool isFrench = (storedLanguage == TestSettings::French && storedLanguage >= 0 && storedLanguage < LanguageCount);
		*language = isFrench ? TestSettings::French : TestSettings::English;

		return true;
	}

	void	WriteLanguageToPreferences (TestSettings::Language language)
	{
		const Int32	storedLanguage = (language == TestSettings::French) ? TestSettings::French : TestSettings::English;

		ACAPI_SetPreferences (TestSettingsVersion, (GSSize) sizeof (Int32), &storedLanguage);
	}

	TestSettings::Language	currentLanguage	= DefaultLanguage ();
	bool					isLoaded			= false;

} /* anonymous namespace */

namespace TestSettings {

	Language	GetLanguage ()
	{
		if (!isLoaded) {
			isLoaded = true;
			ReadLanguageFromPreferences (&currentLanguage);
		}
		return currentLanguage;
	}

	void	SetLanguage (Language language)
	{
		currentLanguage = (language == French) ? French : English;
		isLoaded		= true;
		WriteLanguageToPreferences (currentLanguage);
	}

	void	ToggleLanguage ()
	{
		SetLanguage (GetLanguage () == English ? French : English);
	}

	Int32	GetFirstStringIndex ()
	{
		const Int32	languageOffset = (GetLanguage () == French) ? ID_TEST_STR_LANG_COUNT : 0;

		return ID_TEST_STR_FIRST + languageOffset;
	}

} /* namespace TestSettings */
