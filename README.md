# TEST — add-on Archicad (.apx), bilingue Français / English

Environnement complet de développement, compilation, validation et livraison
d’un add-on Archicad au format `.apx`, basé sur les outils **officiels**
Graphisoft (template CMake + scripts de build + releases officielles du
DevKit).

| Champ | Valeur |
|---|---|
| Nom affiché | `TEST` |
| Description | Palette vide pour commencer (interface disponible en français et en anglais) |
| Developer ID / Local ID Graphisoft (MDID) | enregistrés sur le portail développeur Archicad, définis dans [`RFIX/AddOnFix.grc`](RFIX/AddOnFix.grc) — `32500 'MDID'` |
| Versions Archicad livrées | Archicad 29 et Archicad 30 (Windows x64) |
| DevKit officiels utilisés | AC29 → `29.3100`, AC30 → `30.3000` (tags vérifiés contre les releases Graphisoft) |
| Langues | `INT` (anglais international) et `FRA` (français) — **un seul `.apx` bilingue par version** |
| Plateforme de compilation | Windows, `windows-latest`, MSVC x64, GitHub Actions |
| Fichiers livrés | `TEST-AC29.apx`, `TEST-AC30.apx` (artefacts GitHub Actions) |

---

## 1. Origine des outils (aucune chaîne de build parallèle)

Le dépôt n’ajoute pas son propre système de compilation : il **utilise le
template officiel Graphisoft** et son outillage, référencés en submodule.

| Élément | Provenance | Version épinglée |
|---|---|---|
| `Tools/` (CMakeCommon.cmake, BuildAddOn.py, CompileResources.py, AddOn.hpp, AddOn.rc.in, VersionInfo.rc.in, APIDevKitLinks.json, LocalizationMappingTable.py) | [GRAPHISOFT/archicad-addon-cmake-tools](https://github.com/GRAPHISOFT/archicad-addon-cmake-tools) (submodule Git) | commit `542e0899f976237a594c7df9caf75041b6063e34` — celui que la branche `master` du template officiel [GRAPHISOFT/archicad-addon-cmake](https://github.com/GRAPHISOFT/archicad-addon-cmake) référence (support Archicad 30 inclus) |
| Structure de projet (`CMakeLists.txt`, `Src/APIEnvir.h`, en-tête précompilé, `RFIX.win/AddOnMain.rc2`, dossier `RINT/`, `RFIX/`) | [GRAPHISOFT/archicad-addon-cmake](https://github.com/GRAPHISOFT/archicad-addon-cmake) | commit `68b08b00c45152924f8c45b72141237241ad1bc7` |
| API DevKit (en-têtes, bibliothèques, `ResConv`) | [GRAPHISOFT/archicad-api-devkit — releases](https://github.com/GRAPHISOFT/archicad-api-devkit/releases) | téléchargé **uniquement** depuis l’URL de la release officielle, par `Tools/BuildAddOn.py` |
| Documentation API | https://graphisoft.github.io/archicad-api-devkit/ | docs « Archicad 30 C++ API » |
| MDID (developer id / local id) | https://archicadapi.graphisoft.com/profile/add-ons | fournis par le propriétaire du dépôt, utilisés tels quels |

Mettre à jour les outils :

```bash
git submodule update --remote Tools    # puis vérifier CMakeLists.txt / config.json
```

## 2. Arborescence

```
CMakeLists.txt              # appel du GenerateAddOnProject officiel
config.json                 # nom, version, description, langues, copyright (lus par CMakeCommon.cmake)
Tools/                      # submodule GRAPHISOFT/archicad-addon-cmake-tools
Src/
  APIEnvir.h                # en-tête standard du template Graphisoft
  AddOnPrecompiledHeader.hpp# PCH passé à GenerateAddOnProject (GSNew/GSMalloc en premier)
  ResourceIds.hpp           # IDs de ressources #define, partagés C++ et GRC
  AddOnMain.cpp             # CheckEnvironment / RegisterInterface / Initialize / FreeData
  TestPalette.hpp|cpp       # la palette modeless (DG::Palette + ACAPI_RegisterModelessWindow)
  TestMenu.hpp|cpp          # commande de menu « ouvrir/masquer la palette » + textes localisés
  TestSettings.hpp|cpp      # état de langue (persisté via ACAPI_SetPreferences)
RINT/AddOn.grc              # ressources GRC anglaises (nom, description, menu) — langue par défaut
RFRA/AddOn.grc              # ressources GRC françaises (build optionnel AC_ADDON_LANGUAGE=FRA)
RFIX/AddOnFix.grc            # 'MDID' (developer id + local id) et 'GICN' (icône) — indépendant de la langue
RFIX/TestPalette.grc        # 'STR#' bilingue + 'GDLG'/'DLGH' de la palette — indépendant de la langue
RFIX/Images/AddOnIcon_18x18.svg
RFIX.win/AddOnMain.rc2      # ressource native Windows (icône ACAP.ico du DevKit)
.github/workflows/build.yml # CI Windows : matrice AC29/AC30, cache DevKit, artefacts .apx
.github/scripts/verify_apx.py# validation binaire du .apx (PE x64, ressources, chaînes par langue)
.github/scripts/read_config.py# exporte l'identite de config.json vers la CI ($GITHUB_ENV)
Scripts/new_addon.py         # genere un NOUVEAU projet a partir de ce modele (voir §11)
```

**Ressources au format GRC Graphisoft** : la syntaxe est celle du template
(`'STR#'`, `'GDLG'`, `'DLGH'`, `'MDID'`, `'GICN'`) compilée par `ResConv`
(`Support/Tools/Win/ResConv.exe`) appelé par `Tools/CompileResources.py` —
aucune syntaxe Apple Rez (`resource 'RINT' (...)`, `dialog`, `item`).

Noms **réellement observés** dans le `.apx` Windows après compilation par
`ResConv` (contrôlés par `.github/scripts/verify_apx.py`, qui lit la table de
ressources du PE) :

| Dans le `.grc` | Type Windows dans le `.apx` | id |
|---|---|---|
| `'STR#'` | `STRS` | 32000 (nom + description), 32500 (menu), 32530 (chaînes de la palette) |
| `'GDLG'` | `GSDG` | 32400 (la palette) |
| `'DLGH'` | `DLGH` | 32400 |
| `'MDID'` | `MDID` | 32500 |
| `'GICN'` + `RFIX/Images/*.svg` | `GROUP_ICON` (+ `ICON`, `ANICURSOR`) | 1, `I10001&96`, `I10001&192` (+ `…&D` en mode sombre sur AC30) |
| (posé par `Tools/AddOn.rc.in`) | `STRS` | 18000 (code de langue de l’add-on) |

`ResConv` renomme donc `STR#`→`STRS` et `GDLG`→`GSDG` sur Windows, et
transforme le `GICN` + SVG en véritables groupes d’icônes Windows (les
variantes `&96`/`&192` sont les résolutions 1×/2× ; `&D` est la variante
sombre, générée à partir d’Archicad 29.3000 par `SVGColorChange.py`).
Les identifiants numériques sont des `#define` de `Src/ResourceIds.hpp` :
`CompileResources.py` prétraite chaque `.grc` avec
`cl /EP /I <DevKit>/Inc /I <DevKit>/Modules/DGLib /I Src`, donc seules des
macros préprocesseur y sont visibles (les `constexpr` C++ ne le seraient pas).

## 3. Langues : un seul `.apx` bilingue par version

L’outillage officiel compile, pour une langue donnée, `R<LANG>/*.grc` +
`RFIX/*.grc`. Pour livrer **un** `.apx` par version contenant les deux langues
(commandé), l’architecture retenue est la suivante :

* `RFIX/TestPalette.grc` contient **une seule** table `'STR#' ID_TEST_STRINGS`
  (32530) qui renferme les deux langues : index 1-4 anglais, index 5-8
  français. Étant dans `RFIX/`, elle est compilée dans **tous** les builds.
* L’interface de la palette est écrite dans le `.apx` sous forme neutre, puis
  le texte est appliqué à l’exécution avec les fonctions officielles du module
  DG : `DGSetDialogTitle ()` et `DGSetItemText ()` (déclarées dans
  `<DevKit>/Support/Modules/DGLib/DG.h`).
* La langue active est choisie par l’utilisateur avec le bouton de la palette
  (« Français » ⇄ « English ») ; elle est mémorisée dans les préférences
  Archicad de l’add-on (`ACAPI_GetPreferences` / `ACAPI_SetPreferences`) et
  s’applique aussi au libellé de la commande de menu
  (`ACAPI_MenuItem_SetMenuItemText`).
* Par défaut, la langue est celle du build (`ADDON_LANGUAGE`, défini par
  `Tools/CMakeCommon.cmake`) : `INT` pour le livrable CI.
* Le nom et la description affichés dans *Options > Gestionnaire d’add-ons*
  proviennent de `RINT/AddOn.grc` (ou `RFRA/AddOn.grc`) : ils suivent la langue
  du build. Le nom `TEST` étant identique dans les deux langues, seul le
  descriptif diffère. Pour un `.apx` dont le descriptif serait français, lancer
  un build `AC_ADDON_LANGUAGE=FRA` (ou `python Tools/BuildAddOn.py --configFile
  config.json -l` pour générer un `.apx` par langue) — ce n’est **pas** le
  livrable par défaut.

Codes de langue : `INT` et `FRA`, c’est-à-dire les `VERSION_APPENDIX` définis
par `<DevKit>/Support/Inc/GSLocalization.h` (francophone `FRA` =
`WIN_LANGCHARSET_STR "040C04E4"`), ce sont eux que lit
`Tools/LocalizationMappingTable.py`.

## 4. Comportement de l’add-on

* Enregistrement d’une commande **Extras > TEST Palette**
  (`ACAPI_MenuItem_RegisterMenu`, `MenuCode_Extras`, `MenuFlag_Default`).
* La commande ouvre / masque une **palette modeless** (`'GDLG' … Palette |
  grow | close`, id 32400, dans la plage 32400-32499 imposée par la
  documentation « Modeless Palettes »), créée avec `DG::Palette` et déclarée à
  l’API avec `ACAPI_RegisterModelessWindow` (GUID figé → palette dockable et
  état mémorisé dans l’environnement de travail). Les messages
  `APIPalMsg_*` sont traités (masquer/afficher avec les autres palettes,
  activation/désactivation pendant une saisie, `APIPalMsg_IsPaletteVisible`).
* La palette est volontairement **vide** : une ligne d’information, un
  séparateur, le bouton de langue. C’est le point de départ attendu.
* `ACAPI_UnregisterModelessWindow` est appelé dans `FreeData`.

Fonctions / signatures vérifiées dans les en-têtes réels du DevKit (et non
inventées) : `DG::Palette (GSResModule, short, GSResModule, const GS::Guid&)`,
`DG::ModelessBase::Show/Hide/IsVisible/Activate`, `DG::Panel::GetId`,
`DG::Button (const Panel&, short)`, `DGSetItemText`, `DGSetDialogTitle`,
`ACAPI_RegisterModelessWindow`, `ACAPI_UnregisterModelessWindow`,
`ACAPI_MenuItem_*`, `ACAPI_Get/SetPreferences`, `RSGetIndString`,
`GSGuid2APIGuid`. L’étape « Verify the add-on against the real DevKit headers »
du workflow imprime ces déclarations, extraites du DevKit **téléchargé par le
build**, dans le résumé du job.

## 5. Compatibilité Archicad 29 / 30

| Version | DevKit | Générateur CMake | C++ | Particularités prises en compte |
|---|---|---|---|---|
| Archicad 29 | `29.3100` | Visual Studio 17 2022, toolset `v143` (choisi par `BuildAddOn.py`) | `cxx_std_20` (`CMakeCommon.cmake`: `cxx_std_20` à partir d'Archicad 29) | chemins `Lib/ACAP_STAT.lib` (≥ 27) ; `API_PalEnabled_ModelCompare` disponible |
| Archicad 30 | `30.3000` | Visual Studio 17 2022, toolset `v143` | `cxx_std_20` | `ACAPI_RegisterModelessWindow` accepte un 4ᵉ paramètre par défaut (`APINULLGuid`) ; `ResConv` est appelé avec `-py/-sc` par `CompileResources.py` (icônes sombre/clair) |

Le code n’utilise que l’API présente sur les deux versions : **aucune
adaptation conditionnelle par version n’est nécessaire** pour cette palette.
`AC_ADDON_FOR_DISTRIBUTION` est posé par le build (`-r`) pour que le `.apx` ne
soit pas marqué « private build / prerelease » dans ses métadonnées Windows.

Ajouter Archicad 27 / 28 plus tard : ajouter des lignes dans la matrice
(`devkitTag: 27.6003` et `28.4001`, présents dans `Tools/APIDevKitLinks.json`),
et prévoir que ces versions sont compilées en C++17 avec le toolset `v142`
(choisi automatiquement par `BuildAddOn.py`) : le code actuel reste
compatible, mais il n’a **pas** été compilé pour ces versions ici.

## 6. Compiler localement (Windows)

Prérequis : Visual Studio 2022 (workload *Desktop C++*, toolset `v143`),
CMake ≥ 3.19, Python ≥ 3.10, un environnement MSVC dans le `PATH`
(`cl.exe`/`rc.exe` sont appelés par `CompileResources.py`).

```bat
git clone https://github.com/nuancearchitect-commits/ADDON-TEST.git --recurse-submodules
cd ADDON-TEST
:: depuis une invite "x64 Native Tools Command Prompt for VS 2022"
python Tools\BuildAddOn.py --configFile config.json -v 30 -b Release
:: le livrable : Build\TEST\30\INT\Release\TEST.apx
```

Autres commandes utiles :

```bat
:: une langue par .apx (non livré par défaut)
python Tools\BuildAddOn.py --configFile config.json -v 30 -b Release -l
:: DevKit local déjà décompressé (une seule version à la fois)
python Tools\BuildAddOn.py --configFile config.json -v 30 -n 3000 -d C:\ADK\Support -b Release
:: génération manuelle d’un projet VS
cmake -B Build\Manual -G "Visual Studio 17 2022" -A x64 -T v143 -DAC_VERSION=30 -DAC_API_DEVKIT_DIR=C:\ADK\Support
```

`Build/`, `dist/`, les `.apx`, les caches DevKit et `__pycache__` sont exclus
par `.gitignore`.

## 7. CI : `.github/workflows/build.yml`

Déclenchements : poussée sur `arena/**` ou `main`, et `workflow_dispatch`.
Matrice : `windows-latest` × {Archicad 29, Archicad 30}, un job par version
(`fail-fast: false`), chaque job :

1. checkout **avec le submodule `Tools`** ;
2. Python 3.11 + `ilammy/msvc-dev-cmd` (environnement MSVC x64) ;
3. résolution du DevKit depuis `Tools/APIDevKitLinks.json` et **contrôle croisé
   du tag** avec la matrice (échec explicite si les deux divergent), puis
   vérification de la présence de l’asset dans la release officielle via
   l’API GitHub ;
4. cache `actions/cache` sur `Build/DevKit/APIDevKit-<version>` (clé
   `version + tag DevKit + hash d’APIDevKitLinks.json`) ; un *cache miss*
   n’est pas une erreur : `BuildAddOn.py` télécharge alors le DevKit ;
5. `python Tools/BuildAddOn.py --configFile config.json -v <ver> -b Release
   --forDistribution` (journal sauvegardé en artefact) ;
6. impression dans le résumé du job des déclarations réelles du DevKit
   (`DG::Palette`, `DGSetItemText`, `ACAPI_RegisterModelessWindow`,
   `API_PalEnabled_*`, codes de langue) ;
7. localisation du `.apx` produit, contrôle de taille, copie en
   `dist/TEST-AC<ver>.apx`, exécution de `.github/scripts/verify_apx.py`
   (PE x64 + DLL, présence des chaînes **anglaise et** française, parcours de la
   table de ressources du PE pour vérifier que chaque ressource GRC attendue est
   là, IDs `MDID`), puis `upload-artifact` (`if-no-files-found: error`).
   Le rapport complet de cette vérification est écrit dans le résumé du job *et*
   en annotation, même en cas d’échec ; le SHA-256 du livrable est affiché.

En cas d’échec, l’étape « Failure diagnostics » recherche la **première**
erreur réelle (`error C…`, `error RC…`, `LNK…`, `CMake Error`, `AssertionError`
de `ResConv`…), affiche les lignes autour, le fichier source incriminé et le
`.grc` prétraité autour de la ligne fautive dans `GITHUB_STEP_SUMMARY`.
Les journaux sont téléversés même en cas d’échec. **Aucun secret** n’est
utilisé ni affiché, et le workflow ne publie ni ne remplace une release.

Convention de livraison : une poussée dont le message de commit commence par
`[wip]` construit les `.apx` **sans** `--forDistribution` (build signalé
« private »), sans jamais publier de release.

## 8. Builds validés par la CI (Preuves)

Chaque poussée sur `arena/**` ou `main` reconstruit et re-vérifie les deux `.apx` :
le contrôle de complétude fait partie du workflow, donc un run vert **est** la
preuve que les livrables existent et contiennent les ressources FR+EN.
Run documenté ci-dessous :
[Actions run 44626545033](https://github.com/nuancearchitect-commits/ADDON-TEST/actions/runs/44626545033)
— 2 jobs, `Archicad 29 (DevKit 29.3100)` et `Archicad 30 (DevKit 30.3000)`,
toutes les étapes vertes, y compris « Locate, check and verify the produced .apx »
dont le rapport complet est dans le résumé de chaque job. Dernier run du HEAD en
date : [44626818970](https://github.com/nuancearchitect-commits/ADDON-TEST/actions/runs/44626818970)
(pareillement vert ; ne peut pas se référencer lui-même, le commit qui changerait
le lien déclenchant un nouveau run).

| Livrable | Artefact Actions | Taille | SHA-256 (run 44626545033) |
|---|---|---|---|
| `TEST-AC29.apx` | `TEST-AC29-apx` (zip 35 615 o) | 185 856 o | `9643503aa85c510baf9e6499cffa72e7261c626682e69bd5cbd4faa79b63fa79` |
| `TEST-AC30.apx` | `TEST-AC30-apx` (zip 30 203 o) | 54 272 o | `699b1213adeb78b9dc0a990101278bd4d96b8e31e8de552afa4cb128bfb340cc` |
| journal de compilation | `build-log-ac29`, `build-log-ac30` | ~1,1 Ko chacun | — |

⚠️ le SHA-256 change à chaque rebuild : `link.exe` horodate le PE (TimeDateStamp)
et la compilation n’est **pas reproductible** octet pour octet. Le SHA affiché
dans l’annotation du run sert à identifier **ce** build, pas à valider un
téléchargement ultérieur ; la taille et la table de ressources, elles, sont
stables.

Contrôles passés pour **les deux** `.apx` (visibles en annotation du job et dans
le résumé) :

* binaire `PE32+`, machine `x64 (AMD64)`, drapeau DLL positionné, 6 sections
  (`.text, .rdata, .data, .pdata, .rsrc, .reloc`) ;
* chaîne anglaise *« Empty palette - starting point of your add-on. »* trouvée
  (encodage cp1252, celui de `ResConv` sous Windows) ;
* chaîne française *« Palette vide - point de départ de votre add-on. »* trouvée ;
* chaîne descriptive du Gestionnaire d’add-ons (*RINT*) trouvée ;
* `'MDID'` : `944130148` et `2158966927` présents, et trouvés **collés l’un à
  l’autre** dans le binaire (layout réel de la ressource) ;
* table de ressources du PE parcourue : `STRS` ids `32000/32500/32530`,
  `GSDG` id `32400`, `DLGH` id `32400`, `MDID` id `32500`,
  `GROUP_ICON` avec les entrées `I10001&96` / `I10001&192` (et `&D` en sombre
  sur AC30) — donc les `.grc` ont bien été compilés par `ResConv` et liés.

Récupérer les `.apx` (dépôt public) :

```bash
gh run download 44626545033 --repo nuancearchitect-commits/ADDON-TEST --name TEST-AC29-apx
gh run download 44626545033 --repo nuancearchitect-commits/ADDON-TEST --name TEST-AC30-apx
```

ou via la page du run, section *Artifacts*. L’artefact contient
`dist/TEST-AC<version>.apx`, renommable tel quel : Archicad charge n’importe
quel fichier `.apx` déclaré dans le Gestionnaire d’add-ons (le nom de fichier
n’est pas significatif, c’est le contenu `STRS`/`MDID` qui l’est).

## 9. Vérifier l’add-on dans Archicad (à faire manuellement)

La CI prouve la compilation et la complétude du binaire ; elle ne lance **pas**
Archicad. Tests manuels recommandés, par version (29 et 30) :

1. télécharger l’artefact `TEST-AC<version>-apx` et renommer le fichier en
   `TEST.apx` si besoin ;
2. Archicad → *Options > Gestionnaire d’add-ons…* → **Ajouter…**, sélectionner
   le `.apx`, puis *Enregistrer* et redémarrer Archicad ;
3. contrôler que l’entrée apparaît avec le nom `TEST` et la description
   choisie, sans avertissement lié à l’MDID invalide (les developer id / local id
   doivent correspondre à l’enregistrement du portail Graphisoft) ;
4. menu **Extras > TEST Palette** : la palette s’ouvre (fenêtre dockable,
   fermable = masquée) ;
5. cliquer sur **Français** : ligne d’information, titre et bouton passent en
   français ; le libellé de la commande de menu suit ; refermer Archicad,
   le rouvrir : la langue choisie est conservée (préférences de l’add-on) ;
6. tester *Fenêtres > Palettes flottantes > Tout masquer/afficher*, le passage
   d’un window (plan, 3D, coupe…) à un autre, l’ouverture d’un autre projet, et
   l’enregistrement de l’environnement de travail ;
7. sans projet ouvert, vérifier que l’add-on se charge sans erreur.

## 10. Limitations connues

* Le chargement et le comportement de l’add-on n’ont **pas** été testés dans
  Archicad ici (aucune installation Archicad accessible) : la validation porte
  sur la compilation, les ressources et le binaire. La CI ne lance **pas**
  Archicad : un job vert prouve que le `.apx` compile, qu’il contient les
  ressources FR+EN et qu’il est structurellement valide — pas que la palette
  s’ouvre (voir §9 pour le test manuel).
* Les identifiants MDID sont utilisés tels que fournis. Le `local id`
  (`2158966927`) dépasse 2³¹−1 : `ResConv` l’accepte **et** l’écrit dans le
  `.apx` (vérifié : les deux nombres sont présents, collés l’un à l’autre dans
  la ressource `MDID` 32500). Ce qu’Archicad en pense au chargement n’a pas pu
  être testé ici ; s’il le refuse, la correction doit partir du portail
  développeur Graphisoft, pas d’un changement d’ID dans le dépôt.
* Le descriptif affiché dans le Gestionnaire d’add-ons suit la langue du build, pas le sélecteur FR/EN de la palette (voir §3).
* `RFIX.win/AddOnMain.rc2` référence `ACAP.ico`, qui n’est **pas** dans le dépôt :
  il vient de `Support/Inc` du DevKit (ajouté aux répertoires d’inclusion par
  `Tools/CMakeCommon.cmake`). Les builds CI AC29 et AC30 le résolvent, donc le
  fichier d’icône est bien trouvé ; en cas de changement de structure du DevKit
  cette étape serait la première à casser (`error RC2135`).
* `macOS` n’est pas construit ici (le template le permettrait, la demande
  porte sur Windows).

## 11. Réutiliser ce dépôt comme départ pour un autre add-on

Le modèle est **volontairement sans nom de produit câblé** : tout part de
`config.json` (nom, description, langues, version) et des fichiers `.grc`.
Ni le workflow ni le script de vérification ne citent `TEST`. Une seule façon de
partir de là, décrite étape par étape ; les deux sections suivantes ne sont que
des variantes de confort.

### Les étapes, dans l'ordre (c'est la voie normale)

**1 — Cloner le dépôt et le renommer du nom de l'add-on.**

```bash
git clone --recurse-submodules https://github.com/nuancearchitect-commits/ADDON-TEST.git WallKit
cd WallKit
```

**2 — Remplir `addon.json`, à la racine du dépôt.** Le fichier est déjà là, vide
de son contenu utile (`FILL-ME`). C'est la seule chose à écrire.

```json
{
  "name": "WallKit",
  "description": "Outils de murs - custom wall tools",
  "developerId": 944130148,
  "localId": 2158966928,
  "version": "1.0.0",
  "languages": ["INT", "FRA"],
  "acVersions": [29, 30],
  "copyrightName": "nuancearchitect",
  "repository": { "initGit": true }
}
```

**3 — Lancer le script, sans argument.**

```bash
python Scripts/new_addon.py
```

Il lit `addon.json`, voit qu'il n'y a pas de `--dest`, et transforme **ce clone**
en projet : renommage de l'identité, `config.json`, bloc `'MDID'`, GUID de
palette, dossiers de langue, matrice AC et déclencheurs du workflow, README du
projet, auto-vérification, puis commit sur la branche courante. `addon.json` est
réécrit avec les valeurs appliquées : le fichier reste la carte d'identité du
projet.

**4 — Pousser sur GitHub, et ouvrir Arena sur ce dossier.**

```bash
gh repo create WallKit --source . --private --remote origin --push
```

Le premier build part tout seul (le workflow a été recalé sur la branche où l'on
se trouve, plus les pull requests) et dépose `WallKit-AC29.apx` et
`WallKit-AC30.apx` en artefacts. Pour suivre le run depuis le terminal : ajouter
`"watchCi": true` dans le bloc `repository` avant l'étape 3, ou `gh run watch`.

**5 — Développer.** Les ressources se touchent dans `RINT/AddOn.grc`,
`RFRA/AddOn.grc` et `RFIX/*.grc`, les ids se déclarent dans
`Src/ResourceIds.hpp`, le code dans `Src/WallKit*.cpp`. Un commit préfixé
`[wip]` produit un `.apx` marqué « non distribuable » ; `python
Tools/BuildAddOn.py --configFile config.json -v 30 -b Release -r` refait le même
build que la CI en local.

Ce que les étapes 1→3 remplacent, et ce qui reste manuel : cocher **Template
repository** dans *Settings* du dépôt modèle (l'API GitHub ne l'expose pas), et
merger `arena/23416127-addon-test` sur `main` pour que les clones futurs
partent bien de ce travail.

### a) Génération simple, sans toucher au dépôt

```bash
python Scripts/new_addon.py \
  --name WallKit \
  --description "Outils de murs - custom wall tools" \
  --developer-id 944130148 --local-id 2158966928 \
  --dest ../WallKit \
  --languages INT,FRA --ac-versions 29,30
```

Il copie les 24 fichiers suivis par git (jamais `Build/`, jamais le contenu de
`Tools/`, jamais `.gitmodules` : le projet généré enregistre lui-même le
sous-module), puis :

* renomme l'identité partout : classes/fichiers `Test*` → `WallKit*`, macros
  `ID_TEST_*` → `ID_WALLKIT_*`, titre/description `'STR#'`, garde d'en-tête du
  PCH, titres de la palette ;
* réécrit `config.json` (nom, description, version, langues, copyright) ;
* remplace les deux nombres du bloc `'MDID'` par ceux passés en argument
  (**obligatoires** : rien n'est inventé ni réutilisé d'un autre add-on) ;
* régénère un **GUID de palette** aléatoire (sinon la nouvelle fenêtre hériterait
  de la position mémorisée de l'ancienne) ;
* écrit un `README.md` pour le nouveau projet et conserve cette documentation
  sous `TEMPLATE.md` ;
* règle la matrice AC de `.github/workflows/build.yml` (un tag DevKit inconnu →
  `'FILL-ME'`, donc la CI refuse de deviner) et remplace ses déclencheurs par la
  branche du projet + ses pull requests ;
* crée les dossiers de langue `R<XXX>/` manquants à partir de `RINT/` en écrivant
  un `TODO: translate` en tête (une copie non traduite n'est pas une
  localisation), et retire ceux qui ne sont pas dans `config.json` ;
* **auto-vérifie** le résultat : chaque id utilisé par un `.grc` est bien un
  `#define` de `Src/ResourceIds.hpp`, chaque `#include` local existe, et aucun
  token `TEST`/`Test` ne traîne. Sortie non nulle si une de ces règles casse.

Sans option de dépôt, il affiche les commandes `git init` / `git submodule add …
Tools` / `git -C Tools checkout <sha épinglé>` à coller. Avec `--init-git` (ou
`--create-repo`, ou `--remote-url`), il les exécute : `git init -b main`,
`git submodule add <url> Tools` **check-outé au commit épinglé par le modèle**
(lu via `git ls-files -s Tools`, donc pas la dernière version du dépôt de
Graphisoft), `git add -A`, premier commit, puis `git push` vers `remoteUrl` ou
`gh repo create <name> --source . --remote origin --private --push`. Échouer ne
casse rien : un `gh` absent ou non authentifié, une identité git manquante,
impriment un message et laissent le projet généré intact (le push est sauté
tant que le commit n'existe pas, jamais un push sur une ref inexistante).
`--watch-ci` attend le premier run et le suit (`gh run watch --exit-status`),
`--visibility public` avertit avant de publier les sources. Le projet généré n'a
**aucun** secret et se construit exactement comme ici.

Le dossier `Scripts/` étant copié lui aussi, chaque nouveau projet peut à son
tour servir de modèle (`python Scripts/new_addon.py …` y fonctionne pareil) :
rien n'oblige à repasser par ce dépôt une fois le premier add-on livré.

### b) À la main (cloner puis retoucher 5 endroits)

```bash
git clone --recurse-submodules https://github.com/nuancearchitect-commits/ADDON-TEST.git MonAddOn
cd MonAddOn && git remote remove origin     # repartir de zéro côté remote
```

`config.json`, le bloc `'MDID'` de `RFIX/AddOnFix.grc`, les chaînes de
`RINT/AddOn.grc`, le GUID de `Src/TestPalette.cpp`, la matrice du workflow. Le
reste (outillage, cache, vérification, artefacts) suit automatiquement. C'est
exactement ce que fait `--in-place`, si l'on préfère comprendre avant de laisser
le script écrire.

### Ce qui est réutilisé tel quel, et pourquoi ça tient

| Élément | Comportement pour un nouveau projet |
|---|---|
| `Tools/` (sous-module épinglé) | mêmes scripts officiels ; `BuildAddOn.py` télécharge le DevKit de **chaque** version de la matrice |
| `.github/workflows/build.yml` | nom du livrable, langues et attente de ressources lus dans `config.json` ; artefacts `<addOnName>-AC<ver>-apx` |
| `.github/scripts/verify_apx.py --auto-from .` | **relit les `.grc` du projet** pour reconstituer les ids de ressources et les chaînes UI à trouver dans le binaire : pas de liste à maintenir à la main quand on ajoute une ressource |
| Convention `[wip]` | même règle : message de commit commençant par `[wip]` → build sans `--forDistribution` |

Un projet généré par `new_addon.py` est donc **aussi** validé par la CI dès la
première poussée : si un `.grc` déclare une ressource que `ResConv` n'a pas liée,
le job rouge avec la ligne exacte du rapport de vérification.

### Ajouts futurs usuels

* **Autre version d'Archicad** : une ligne dans la matrice + vérifier le tag dans
  `Tools/APIDevKitLinks.json` (le CI refuse déjà une divergence).
* **Autre langue** : l'ajouter à `languages` de `config.json` + créer `R<XXX>/`.
* **Plusieurs `.apx` localisés** (un par langue) plutôt qu'un bilingue :
  `python Tools/BuildAddOn.py --configFile config.json -l` — voir §3.
* **Dépôt modèle GitHub** : marquer ce dépôt « Template repository » dans *Settings*
  permet `gh repo create MonAddOn --template nuancearchitect-commits/ADDON-TEST` ;
  ce drapeau se règle dans l'interface GitHub (l'API ne l'expose pas à la
  modification), puis le script ci-dessus reste utile pour l'identité.
