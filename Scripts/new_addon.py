#!/usr/bin/env python3
"""Create a new Archicad add-on project from this template.

Copy the tested skeleton (official Graphisoft build tools, bilingual GRC
resources, palette + menu + preferences, Windows CI that builds and verifies one
.apx per Archicad version) into a new folder, rename everything that carries the
product identity, and print what must still be checked by hand.

    python Scripts/new_addon.py \
        --name WallKit \
        --description "Outils de murs - custom wall tools" \
        --developer-id 944130148 --local-id 2158966928 \
        --dest ../WallKit

The two Graphisoft identifiers must come from your registration on the Archicad
developer portal (https://archicadapi.graphisoft.com/profile/add-ons): each add-on
needs its own 'local id'. Nothing is invented or reused here - if you do not pass
them, the script stops.
"""

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import uuid

# The DevKit build number of each Archicad version as published by
# Tools/APIDevKitLinks.json at the commit pinned in this template. The CI
# cross-checks the matrix against that file, so a stale value fails loudly.
DEVKIT_TAGS = {'26': '26.411', '27': '27.6003', '28': '28.4001', '29': '29.3100', '30': '30.3000'}

# Ordered: long identifiers first, the bare display name last.
# {Name} is the add-on name, {NAMEUP} its upper case form.
RENAME_RULES = [
    ('TESTPalette', '{Name}Palette'),
    ('TestPalette', '{Name}Palette'),
    ('TESTPALETTE', '{NAMEUP}_PALETTE'),
    ('TestMenu', '{Name}Menu'),
    ('TESTMENU', '{NAMEUP}_MENU'),
    ('TestSettings', '{Name}Settings'),
    ('TESTSETTINGS', '{NAMEUP}_SETTINGS'),
    ('ID_TEST_', 'ID_{NAMEUP}_'),
    ('DLG_Test_Palette', 'DLG_{Name}_Palette'),
    ('"TEST"', '"{Name}"'),
    ('TEST Palette', '{Name} Palette'),
    ('TEST_ADDON_PRECOMPILED_HEADER_HPP', '{NAMEUP}_ADDON_PRECOMPILED_HEADER_HPP'),
    ('TEST - a bilingual', '{Name} - a bilingual'),
    ('Palette TEST', 'Palette {Name}'),
    ('TEST palette', '{Name} palette'),
    ('the TEST add-on', 'the {Name} add-on'),
    ('TEST add-on', '{Name} add-on'),
]

TEXT_SUFFIXES = {'.cpp', '.hpp', '.h', '.grc', '.rc2', '.json', '.yml', '.yaml', '.md', '.svg', '.in'}
# the template documentation is kept as-is, so its own name is not a leftover
CHECK_SUFFIXES = {'.cpp', '.hpp', '.h', '.grc', '.rc2', '.json', '.yml', '.yaml', '.svg'}
EXCLUDED_DIRS = {'Build', 'dist', 'out', '__pycache__', '.vs', '.vscode', 'node_modules'}
TEMPLATE_TOKENS = ('TEST', 'Test')


def run (args, cwd = None, capture = True):
    """Run a command and return the CompletedProcess: every caller decides what is fatal."""
    return subprocess.run (args, cwd = str (cwd) if cwd else None, capture_output = capture, text = True)


def is_skipped (path, root):
    """Never rewrite the Tools submodule, a build tree or the git metadata."""
    try:
        rel = path.relative_to (root)
    except ValueError:
        return True
    return bool (set (rel.parts) & ({'Tools', 'Build', 'dist', 'out', '.git', '__pycache__'} | EXCLUDED_DIRS))


def list_project_files (source: pathlib.Path):
    """The files that make up the template (never a build tree, never Tools/)."""
    out = run (['git', '-C', str (source), 'ls-files'])
    if out.returncode == 0:
        # 'Tools' (the gitlink) and '.gitmodules' are not copied: the new project
        # registers the submodule itself, at the commit pinned by the template.
        skip = {'Tools', '.gitmodules'}
        names = [line for line in out.stdout.splitlines () if line and line not in skip]
        if (source / '.gitignore').is_file () and '.gitignore' not in names:
            names.append ('.gitignore')
        return sorted (names)
    names = []
    for path in sorted (source.rglob ('*')):
        rel = path.relative_to (source)
        if '.git' in rel.parts or EXCLUDED_DIRS.intersection (rel.parts) or not path.is_file ():
            continue
        if str (rel).replace ('\\', '/') in ('.gitmodules', 'Tools'):
            continue
        names.append (str (rel).replace ('\\', '/'))
    return names


def copy_tree (source: pathlib.Path, dest: pathlib.Path, names):
    for rel in names:
        src = source / rel
        if not src.is_file ():
            continue
        dst = dest / rel
        dst.parent.mkdir (parents = True, exist_ok = True)
        shutil.copy2 (src, dst)
    return len (names)


def rename_identifiers (dest: pathlib.Path, name: str):
    upper = name.upper ()
    rules = [(token, template.format (Name = name, NAMEUP = upper)) for token, template in RENAME_RULES]
    touched = 0
    for path in sorted (dest.rglob ('*')):
        if not path.is_file () or path.suffix.lower () not in TEXT_SUFFIXES:
            continue
        if is_skipped (path, dest):
            continue
        try:
            text = path.read_text (encoding = 'utf-8')
        except UnicodeDecodeError:
            continue
        new_text = text
        for token, replacement in rules:
            new_text = new_text.replace (token, replacement)
        if new_text != text:
            path.write_text (new_text, encoding = 'utf-8')
            touched += 1

    # then the file names, so that the #include lines rewritten above resolve
    renamed = []
    for path in sorted (dest.rglob ('*')):
        base = path.name
        if not path.is_file () or not base.startswith ('Test'):
            continue
        if is_skipped (path, dest):
            continue
        stem = base[4:]
        target = path.with_name (name + stem)
        path.rename (target)
        renamed.append (f'{base} -> {target.name}')
    return touched, renamed


def rewrite_config (dest: pathlib.Path, args):
    path = dest / 'config.json'
    config = json.loads (path.read_text (encoding = 'utf-8-sig'))
    config['addOnName'] = args.name
    config['description'] = args.description
    config['version'] = args.version
    config['defaultLanguage'] = args.languages[0]
    config['languages'] = args.languages
    copyright_info = dict (config.get ('copyright', {}))
    copyright_info['name'] = args.copyright_name
    copyright_info['year'] = '%Y'          # expanded from the build date by CMakeCommon
    config['copyright'] = copyright_info
    path.write_text (json.dumps (config, indent = 4, ensure_ascii = False) + '\n', encoding = 'utf-8')
    return config


def rewrite_mdid (dest: pathlib.Path, args):
    grc = dest / 'RFIX' / 'AddOnFix.grc'
    if not grc.is_file ():
        raise SystemExit (f'::error::{grc} is missing - cannot set the add-on identifiers')
    text = grc.read_text (encoding = 'utf-8-sig')
    text, first = re.subn (r'(?m)^(\s*)\d+(\s*/\* developer id \*/)$',
                           lambda m: f'{m.group (1)}{args.developer_id}{m.group (2)}', text, count = 1)
    text, second = re.subn (r'(?m)^(\s*)\d+(\s*/\* local id \*/)$',
                            lambda m: f'{m.group (1)}{args.local_id}{m.group (2)}', text, count = 1)
    if first != 1 or second != 1:
        raise SystemExit ('::error::the \'MDID\' block of RFIX/AddOnFix.grc was not recognised '
                          '(it needs one number per line, commented "developer id" and "local id")')
    grc.write_text (text, encoding = 'utf-8')


def rewrite_palette_guid (dest: pathlib.Path, args):
    for palette in sorted ((dest / 'Src').glob ('*Palette.cpp')):
        text = palette.read_text (encoding = 'utf-8')
        new_guid = str (uuid.uuid4 ()).upper ()
        text, count = re.subn (r'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}',
                               new_guid, text, count = 1)
        if count:
            palette.write_text (text, encoding = 'utf-8')
            return new_guid
    return None


def rewrite_workflow_matrix (dest: pathlib.Path, args):
    workflow = dest / '.github' / 'workflows' / 'build.yml'
    if not workflow.is_file ():
        return False
    text = workflow.read_text (encoding = 'utf-8')
    marker = re.search (r'(strategy:\n(?:.*\n)*?\s*matrix:\n)(.*?)(?=\n {4}\S|\Z)', text)
    anchor = re.search (r'\n( *)include:\n', text)
    if not anchor:
        return False
    indent = anchor.group (1)
    start = anchor.end ()
    end = start
    while True:
        nl = text.index ('\n', end)
        line = text[end:nl]
        if not line.startswith (indent + '- ') and not line.startswith (indent + '  '):
            break
        end = nl + 1
    block = ''
    for version in args.ac_versions:
        tag = DEVKIT_TAGS.get (str (version))
        block += f'{indent}  - acVersion: {version}\n'
        block += (f"{indent}    devkitTag: '{tag}'\n" if tag else f"{indent}    devkitTag: 'FILL-ME'\n")
    text = text[:start] + block + text[end:]
    workflow.write_text (text, encoding = 'utf-8')
    return True


NEW_README = """# {name} - Archicad add-on (.apx)

Starté from the tested `TEST` add-on template: official Graphisoft build tools
(`Tools/` submodule), bilingual GRC resources, one `.apx` per Archicad version,
Windows CI on GitHub Actions. See [TEMPLATE.md](TEMPLATE.md) for the details of
the environment (tools, DevKit versions, CI, verification).

| | |
|---|---|
| Add-on name (`config.json`) | `{name}` |
| Description (add-on manager) | {description} |
| Developer id / Local id (`'MDID'` in `RFIX/AddOnFix.grc`) | {developer_id} / {local_id} |
| Archicad versions built by CI | {versions} |
| Languages of the `.apx` | {languages} (default build language: {default}) |
| Artefacts | {artifacts} |

## Build

```bash
python Tools/BuildAddOn.py --configFile config.json -v {first_version} -b Release
# -> Build/{name}/{first_version}/{default}/Release/{name}.apx
```

## Where to put your code

| Purpose | File |
|---|---|
| add-on lifecycle (`CheckEnvironment`, `RegisterInterface`, `Initialize`, `FreeData`) | `Src/AddOnMain.cpp` |
| the modeless palette (UI) | `Src/{name}Palette.hpp/.cpp` |
| the menu command | `Src/{name}Menu.hpp/.cpp` |
| persisted state (the FR/EN choice today) | `Src/{name}Settings.hpp/.cpp` |
| resource ids shared by C++ and the .grc | `Src/ResourceIds.hpp` |
| UI strings, dialog layout, icon, `'MDID'` | `RFIX/*.grc` (every language), `{default_folder}/*.grc` (this language only) |
| versions / languages / name | `config.json`, `.github/workflows/build.yml` (matrix) |

Rules that keep the environment working:

* resources are **GRC** files compiled by `ResConv` (no Apple Rez syntax), and every
  id used in a `.grc` must be a `#define` of `Src/ResourceIds.hpp`;
* a new UI string goes to the `'STR#'` table of `RFIX/` (indexed per language) so
  that one bilingual `.apx` is enough;
* do not change the `'MDID'` resource id (32500), and use ids of your own: a palette
  must be in 32400-32499.

## Import in Archicad

Options > Add-ons Manager... > Add... > the `.apx`, restart Archicad, then the
command in the Extras menu.

## Before the first release

Check that your developer id / local id pair matches your registration on
https://archicadapi.graphisoft.com/profile/add-ons, otherwise Archicad will refuse
or flag the add-on.
"""


def write_project_readme (dest: pathlib.Path, args):
    template_readme = dest / 'README.md'
    kept = dest / 'TEMPLATE.md'
    if template_readme.is_file () and not kept.exists ():
        template_readme.rename (kept)
    versions = ', '.join (str (v) for v in args.ac_versions)
    artifacts = ', '.join (f'`{args.name}-AC{v}.apx`' for v in args.ac_versions)
    text = NEW_README.format (
        name = args.name, description = args.description, developer_id = args.developer_id,
        local_id = args.local_id, versions = versions, languages = ', '.join (args.languages),
        default = args.languages[0], default_folder = 'R' + args.languages[0],
        first_version = args.ac_versions[0], artifacts = artifacts)
    template_link = f'[{kept.name}]({kept.name})'
    text = text.replace ('[TEMPLATE.md](TEMPLATE.md)', template_link)
    (dest / 'README.md').write_text (text, encoding = 'utf-8')
    return kept.is_file ()


TOOLS_URL_FALLBACK = 'https://github.com/GRAPHISOFT/archicad-addon-cmake-tools.git'


def read_tools_pin (source: pathlib.Path):
    """The submodule url (from .gitmodules) and the commit pinned by the template."""
    url = ''
    gitmodules = source / '.gitmodules'
    if gitmodules.is_file ():
        match = re.search (r'url\s*=\s*(\S+)', gitmodules.read_text (encoding = 'utf-8'))
        url = match.group (1) if match else ''
    url = url or TOOLS_URL_FALLBACK
    sha = ''
    out = run (['git', '-C', str (source), 'ls-files', '-s', 'Tools'])
    if out.returncode == 0:
        match = re.search (r'\b([0-9a-f]{40})\b', out.stdout)
        sha = match.group (1) if match else ''
    return url, sha


def git (dest: pathlib.Path, *args, optional = False):
    """Run git in dest; report (never abort the generation) when optional."""
    out = run (['git', *[str (a) for a in args]], cwd = str (dest))
    if out.returncode and not optional:
        raise SystemExit (f'::error::git {" ".join (str (a) for a in args)} failed: '
                          f'{(out.stderr or out.stdout).strip ()[:400]}')
    return out


def current_branch (dest: pathlib.Path, default = 'main'):
    """The branch HEAD points at, or `default` when the repository has no commit yet."""
    out = run (['git', '-C', str (dest), 'symbolic-ref', '--quiet', '--short', 'HEAD'])
    return out.stdout.strip () or default


def prepare_repository (dest: pathlib.Path, source: pathlib.Path, args):
    """git init, Tools submodule at the pinned commit, first commit, then the
    GitHub repository. A missing tool is reported as a next step, it never
    destroys the generated project."""
    url, sha = read_tools_pin (source)
    report = []

    branch = 'main'
    if not (dest / '.git').is_dir ():
        git (dest, 'init', '-b', branch)
        report.append ('git init -b main')
    else:
        # cloning a template keeps the branch it was cloned with, do not fight it
        branch = current_branch (dest)
        report.append ('.git already present: kept as is'
                       + ('' if branch == 'main' else f' (pushing to {branch})'))
        if branch != 'main':
            report.append ('::warning::the workflow uploads the .apx only on main (it only checks the build on a pull '
                           f'request): merge {branch} into main, or rename it, to get the artifacts')

    if not (dest / 'Tools' / 'BuildAddOn.py').is_file ():
        if (dest / 'Tools').exists ():
            shutil.rmtree (dest / 'Tools')
        out = git (dest, 'submodule', 'add', url, 'Tools', optional = True)
        if out.returncode:
            report.append ('::error::git submodule add failed: '
                           + (out.stderr or out.stdout).strip ()[:200]
                           + f' - run it by hand: git submodule add {url} Tools')
        else:
            if sha:
                git (dest, '-C', 'Tools', 'checkout', sha, optional = True)
                report.append (f'Tools submodule registered and checked out at {sha[:12]}')
            git (dest, 'add', 'Tools', '.gitmodules', optional = True)
    else:
        report.append ('Tools/ already populated: left untouched')

    git (dest, 'add', '-A')
    commit = git (dest, 'commit', '-m', f'Start {args.name} from the Archicad add-on template',
                  optional = True)
    committed = commit.returncode == 0
    if committed:
        head = git (dest, 'rev-parse', '--short', 'HEAD').stdout.strip ()
        report.append (f'first commit {head}')
    else:
        detail = (commit.stderr or commit.stdout).strip ().splitlines ()
        report.append ('the first commit did NOT happen ('
                       + (detail[-1][:120] if detail else 'unknown reason')
                       + ') - usually the git identity: git config user.name/user.email, then git commit -m "..."')
        report.append ('* nothing was pushed: the repository stays local until the commit exists')
    if not committed and not git (dest, 'rev-parse', 'HEAD', optional = True).returncode:
        committed = True          # an existing repository with history can still be pushed

    if git (dest, 'rev-parse', '--is-shallow-repository', optional = True).stdout.strip () == 'true':
        report.append ('::warning::this clone is shallow, GitHub rejects a push from it '
                       '(shallow update not allowed): run git fetch --unshallow first, then push. '
                       'The generated files are fine, only the push is at risk')

    if args.create_repo and args.remote_url:
        report.append ('::warning::--create-repo and --remote-url given: using --remote-url only')
    if args.remote_url and not committed:
        report.append (f'skipped the push (no commit yet) - commit, then: git push -u origin {branch}')
    elif args.remote_url:
        git (dest, 'remote', 'add', 'origin', args.remote_url, optional = True)
        push = git (dest, 'push', '-u', 'origin', branch, optional = True)
        report.append ('pushed to ' + args.remote_url if push.returncode == 0 else
                       'git push failed: ' + (push.stderr or push.stdout).strip ()[:200])
    elif args.create_repo and not committed:
        report.append ('skipped the GitHub repository creation (no commit yet)')
    elif args.create_repo:
        if not shutil.which ('gh'):
            report.append ('::error::the gh cli is not installed - create the repository yourself, then '
                           f'git remote add origin <url> && git push -u origin {branch}')
        else:
            repo_name = args.repo_name or args.name
            if args.visibility == 'public':
                print ('::warning::creating a PUBLIC repository: the sources become readable by anyone. '
                       'The MDID numbers are not secrets, your code is.')
            create = run (['gh', 'repo', 'create', repo_name, '--source', str (dest), '--remote', 'origin',
                           '--' + args.visibility, '--push',
                           '--description', f'Archicad add-on {args.name}'], cwd = str (dest))
            if create.returncode == 0:
                last = [line for line in create.stdout.strip ().splitlines () if line.strip ()]
                report.append (f'GitHub repository created and pushed ({args.visibility}): '
                               + (last[-1] if last else repo_name))
            else:
                report.append ('::error::gh repo create failed: '
                               + (create.stderr or create.stdout).strip ()[:300])
                report.append (f'you can still run: gh repo create {repo_name} --source "{dest}" '
                               f'--{args.visibility} --remote origin --push')
    else:
        report.append ('no remote configured: add --create-repo (gh) or --remote-url <git url> to push, '
                       'or do it by hand')

    for line in report:
        print (f'* {line}')
    return report


def watch_ci (dest: pathlib.Path, branch = 'main'):
    """Follow the first Actions run of the new project (needs the gh cli)."""
    if not shutil.which ('gh'):
        print ('* the gh cli is not installed: open the Actions tab of the repository to follow the build')
        return
    import time
    run_id = ''
    for attempt in range (6):
        out = run (['gh', 'run', 'list', '--branch', branch, '--limit', '1',
                    '--json', 'databaseId,status,conclusion,url', '--jq', '.[0].databaseId'],
                   cwd = str (dest))
        if out.returncode == 0 and out.stdout.strip () and out.stdout.strip () != 'null':
            run_id = out.stdout.strip ()
            break
        if attempt == 0:
            print ('* the workflow is not registered yet, retrying for a minute '
                   '(GitHub needs the push to land on a repository it knows)')
        time.sleep (10)
    if not run_id:
        print ('* no Actions run detected: if the repository is not on GitHub yet, this is expected. '
              'After the first push: gh run list --limit 3, then gh run watch <id> --exit-status')
        return
    print (f'* following run {run_id} (Ctrl-C only detaches, the build keeps running on GitHub)')
    watch = subprocess.run (['gh', 'run', 'watch', run_id, '--exit-status'], cwd = str (dest))
    if watch.returncode:
        print (f'* the run failed: gh run view {run_id} --log-failed   '
              f'(and the job summary holds the first real error + the .apx verification report)')


def self_check (dest: pathlib.Path):
    problems = []
    notes = []

    ids_header = dest / 'Src' / 'ResourceIds.hpp'
    defines = {}
    if ids_header.is_file ():
        for match in re.finditer (r'#\s*define\s+(ID_[A-Z0-9_]+)\s+(\S+)',
                                  ids_header.read_text (encoding = 'utf-8')):
            defines[match.group (1)] = match.group (2)
    else:
        problems.append ('Src/ResourceIds.hpp is missing')

    grc_files = sorted (list ((dest / 'RFIX').glob ('*.grc')) + [p for d in dest.glob ('R*') for p in d.glob ('*.grc')])
    if not grc_files:
        problems.append ('no .grc resource file found')
    used = set ()
    for grc in grc_files:
        text = grc.read_text (encoding = 'utf-8-sig', errors = 'replace')
        used |= set (re.findall (r"^\s*'[A-Za-z0-9#]{1,4}'\s+(ID_[A-Z0-9_]+)", text, re.M))
        for inc in re.findall (r'#\s*include\s+"([^"]+)"', text):
            if not (dest / 'Src' / inc).is_file ():
                problems.append (f'{grc.relative_to (dest)}: #include "{inc}" not found in Src/ '
                                 f'(ResConv preprocesses the .grc with -I Src)')
    missing = sorted (used - set (defines))
    if missing:
        problems.append (f'ids used in the .grc but not defined in Src/ResourceIds.hpp: {missing}')
    cpp_used = set ()
    for source in sorted ((dest / 'Src').glob ('*')):
        if source.suffix.lower () in ('.cpp', '.hpp', '.h'):
            cpp_used |= set (re.findall (r'\bID_[A-Z0-9_]+\b', source.read_text (encoding = 'utf-8',
                                                                                   errors = 'replace')))
    unused = sorted (set (defines) - used - cpp_used)
    if unused:
        notes.append (f'ids defined but used neither by a .grc nor by the C++ sources: {unused}')

    own_headers = {path.name for path in (dest / 'Src').glob ('*')}
    for source in sorted ((dest / 'Src').glob ('*')):
        if source.suffix.lower () not in ('.cpp', '.hpp', '.h'):
            continue
        text = source.read_text (encoding = 'utf-8', errors = 'replace')
        for inc in re.findall (r'#\s*include\s+"([^"]+)"', text):
            # an include of a DevKit header (ACAPinc.h, DG.h, ...) is resolved by
            # CMake against the DevKit: only the project's own headers are checked.
            if inc in own_headers and not (dest / 'Src' / inc).is_file ():
                problems.append (f'{source.relative_to (dest)}: #include "{inc}" is missing from Src/')

    leftovers = []
    for path in sorted (dest.rglob ('*')):
        if not path.is_file () or path.suffix.lower () not in CHECK_SUFFIXES:
            continue
        if is_skipped (path, dest):
            continue
        if 'new_addon' in path.name:
            continue
        for index, line in enumerate (path.read_text (encoding = 'utf-8', errors = 'replace').split ('\n'), 1):
            if any (token in line for token in TEMPLATE_TOKENS):
                leftovers.append (f'{path.relative_to (dest)}:{index}: {line.strip ()[:90]}')
    return problems, notes, leftovers[:15]


def load_data_file (path):
    """Read the add-on data from a small json/ini file so that starting a project
    is one line: python Scripts/new_addon.py --from addon.json --dest ../WallKit

        {
          "name": "WallKit",
          "description": "Outils de murs - custom wall tools",
          "developerId": 944130148,
          "localId": 2158966928,
          "version": "1.0.0",
          "languages": ["INT", "FRA"],
          "acVersions": [29, 30],
          "copyrightName": "nuancearchitect",
          "repository": {"visibility": "private", "create": true, "watchCi": true}
        }
    """
    file = pathlib.Path (path)
    if not file.is_file ():
        raise SystemExit (f'::error::{file} does not exist')
    text = file.read_text (encoding = 'utf-8-sig')
    try:
        data = json.loads (text)
    except json.JSONDecodeError as error:
        raise SystemExit (f'::error::{file} is not valid json: {error}')
    if not isinstance (data, dict):
        raise SystemExit (f'::error::{file} must hold a single json object')
    return data


KEY_TO_FLAG = {
    'name': '--name',
    'description': '--description',
    'developerId': '--developer-id',
    'localId': '--local-id',
    'version': '--version',
    'copyrightName': '--copyright-name',
}


def data_to_argv (data, given_dests):
    """Turn the data file into command line defaults (flags already given win)."""
    argv = []

    def add (flag, value):
        if flag.lstrip ('-').replace ('-', '_') not in given_dests:
            argv.extend ([flag, str (value)])

    for key, flag in KEY_TO_FLAG.items ():
        if key in data:
            add (flag, data[key])
    if 'languages' in data:
        add ('--languages', ','.join (data['languages']))
    if 'acVersions' in data:
        add ('--ac-versions', ','.join (str (v) for v in data['acVersions']))
    repo = data.get ('repository', {}) or {}
    if 'visibility' in repo:
        add ('--visibility', repo['visibility'])
    if 'name' in repo:
        add ('--repo-name', repo['name'])
    if 'remoteUrl' in repo:
        add ('--remote-url', repo['remoteUrl'])
    if repo.get ('create'):
        argv.append ('--create-repo')
    if repo.get ('initGit', True):
        argv.append ('--init-git')
    if repo.get ('watchCi'):
        argv.append ('--watch-ci')
    return argv


def build_parser ():
    parser = argparse.ArgumentParser (description = 'Create a new Archicad add-on project from this template',
                                      formatter_class = argparse.RawDescriptionHelpFormatter,
                                      epilog = __doc__)
    parser.add_argument ('--name', help = 'add-on name and class prefix, e.g. WallKit')
    parser.add_argument ('--description', help = 'description shown in the add-on manager')
    parser.add_argument ('--developer-id', type = int, help = "Graphisoft developer id ('MDID')")
    parser.add_argument ('--local-id', type = int, help = "Graphisoft local id ('MDID')")
    parser.add_argument ('--dest', help = 'target folder')
    parser.add_argument ('--in-place', dest = 'in_place', action = 'store_true',
                         help = 'transform the CURRENT repository instead of copying elsewhere: use this '
                                'right after cloning the template (git clone --recurse-submodules ...). '
                                'It rewrites the tracked files; undo everything with git checkout -- .')
    parser.add_argument ('--version', default = '1.0.0', help = 'add-on version (config.json)')
    parser.add_argument ('--languages', default = 'INT,FRA',
                         help = 'comma separated language codes, the first one is the default of the build '
                                '(INT = English, FRA = French, DEU, ITA, ESP, NLD, SWE, JPN, CHS...)')
    parser.add_argument ('--ac-versions', default = '29,30', help = 'Archicad versions of the CI matrix')
    parser.add_argument ('--copyright-name', default = None, help = 'copyright holder (default: --name)')
    parser.add_argument ('--template-dir', default = str (pathlib.Path (__file__).resolve ().parent.parent),
                         help = 'folder of this template (default: parent of Scripts/)')
    parser.add_argument ('--force', action = 'store_true', help = 'write into an existing non-empty folder')
    parser.add_argument ('--from', dest = 'data_file', metavar = 'FILE.json',
                         help = 'read the add-on data from a json file (see load_data_file); '
                                'explicit command line flags win over the file')
    parser.add_argument ('--init-git', action = 'store_true',
                         help = 'git init the new project, add the Tools submodule at the pinned commit '
                                'and make the first commit')
    parser.add_argument ('--create-repo', action = 'store_true',
                         help = 'with --init-git: create the GitHub repository with gh and push '
                                '(requires the gh cli authenticated as you)')
    parser.add_argument ('--repo-name', default = None, help = 'GitHub repository name (default: --name)')
    parser.add_argument ('--visibility', default = 'private', choices = ('private', 'public'),
                         help = 'visibility of the created GitHub repository')
    parser.add_argument ('--remote-url', default = None, help = 'existing repository url to push to')
    parser.add_argument ('--watch-ci', action = 'store_true', help = 'follow the first Actions run')
    return parser


def parse_args (argv = None, only_given = False):
    """Parse the command line.

    only_given=True drops the untouched defaults, so the caller can tell what the
    user really typed from what the parser filled in (precedence: command line >
    --from file > built-in defaults).
    """
    parser = build_parser ()
    if only_given:
        for action in parser._actions:
            action.default = argparse.SUPPRESS
    return parser.parse_args (argv)


def main ():
    cli = parse_args (only_given = True)          # what was really typed
    args = vars (parse_args ())                   # with the built-in defaults
    args.update (vars (cli))
    if getattr (cli, 'data_file', None):
        data = load_data_file (cli.data_file)
        from_file = parse_args (data_to_argv (data, set (vars (cli))), only_given = True)
        for key, value in vars (from_file).items ():
            if key not in vars (cli):
                args[key] = value
        if 'dest' not in vars (cli) and data.get ('dest') and not args.get ('dest'):
            args['dest'] = str ((pathlib.Path (cli.data_file).resolve ().parent / data['dest']).resolve ())
    args = argparse.Namespace (**args)

    required = [('--name', args.name), ('--description', args.description),
                ('--developer-id', args.developer_id), ('--local-id', args.local_id)]
    required += [] if args.in_place else [('--dest (or --in-place)', args.dest)]
    required = tuple (required)
    missing = [flag for flag, value in required if value in (None, '')]
    if missing:
        sys.exit ('::error::missing required value(s): ' + ', '.join (missing)
                  + '\n         give them on the command line, or in the --from file with the keys '
                    '"name", "description", "developerId", "localId", "dest"\n'
                    '         (a relative "dest" is resolved from the folder of that file)')
    if not re.fullmatch (r'[A-Z][A-Za-z0-9_]{1,62}', args.name):
        sys.exit (f'::error::--name {args.name!r} must start with a capital letter and be one identifier')
    args.languages = [lang.strip ().upper () for lang in args.languages.split (',') if lang.strip ()]
    for lang in args.languages:
        if not re.fullmatch (r'[A-Z]{3}', lang):
            sys.exit (f'::error::language code {lang!r} must be 3 uppercase letters (INT, FRA, DEU...)')
    try:
        args.ac_versions = [int (v) for v in args.ac_versions.split (',') if v.strip ()]
    except ValueError:
        sys.exit ('::error::--ac-versions must be numbers, e.g. 29,30')
    if not args.ac_versions:
        sys.exit ('::error::--ac-versions is empty')
    if args.developer_id <= 0 or args.local_id <= 0:
        sys.exit ('::error::developer id and local id must be positive numbers from the Graphisoft portal')
    if not args.copyright_name:
        args.copyright_name = args.name

    source = pathlib.Path (args.template_dir).resolve ()
    if not (source / 'config.json').is_file () or not (source / 'RFIX' / 'AddOnFix.grc').is_file ():
        sys.exit (f'::error::{source} is not this template (no config.json / RFIX/AddOnFix.grc)')
    if args.in_place:
        dest = source
        if not (dest / '.git').exists ():
            sys.exit ('::error::--in-place needs a git repository to rewrite (clone the template with '
                      'git clone --recurse-submodules, or use --dest)')
        status = run (['git', '-C', str (dest), 'status', '--porcelain'])
        if status.returncode == 0 and status.stdout.strip ():
            sys.exit ('::error::the working tree is not clean; commit or stash first, because --in-place '
                      'renames files (git status shows what would be mixed up)')
        print (f'* transforming this repository in place: {dest}')
    else:
        if not args.dest:
            sys.exit ('::error::--dest is required (or use --in-place inside a fresh clone of the template)')
        dest = pathlib.Path (args.dest).resolve ()
        if dest == source:
            sys.exit ('::error::--dest must not be the template itself (use --in-place to transform a clone)')
        if dest.exists () and any (p for p in dest.iterdir () if p.name != '.git') and not args.force:
            sys.exit (f'::error::{dest} exists and is not empty (use --force to write into it)')
        dest.mkdir (parents = True, exist_ok = True)

    if args.in_place:
        names = list_project_files (source)
        print (f'* {len (names)} tracked files, renamed in place')
    else:
        names = list_project_files (source)
        copied = copy_tree (source, dest, names)
        print (f'* {copied} template files copied to {dest}')

    touched, renamed = rename_identifiers (dest, args.name)
    print (f'* identity renamed in {touched} files; files renamed: {", ".join (renamed) or "none"}')
    config = rewrite_config (dest, args)
    print (f"* config.json: addOnName={config['addOnName']}, languages={config['languages']}, "
          f"default={config['defaultLanguage']}, version={config['version']}")
    rewrite_mdid (dest, args)
    print (f"* 'MDID': developer id {args.developer_id}, local id {args.local_id}")
    guid = rewrite_palette_guid (dest, args)
    if guid:
        print (f'* new palette GUID: {guid}')
    if write_project_readme (dest, args):
        print ('* README.md written for the new add-on; the template documentation is TEMPLATE.md')
    if rewrite_workflow_matrix (dest, args):
        unknown = [v for v in args.ac_versions if str (v) not in DEVKIT_TAGS]
        print (f'* CI matrix: Archicad {", ".join (str (v) for v in args.ac_versions)}'
              + (f' - FILL-ME the DevKit tag of {unknown}, then check Tools/APIDevKitLinks.json' if unknown else ''))

    # the language folders: create the ones the build needs, from the first one
    folders = {lang: dest / f'R{lang}' for lang in args.languages}
    template_folder = dest / f'R{args.languages[0]}'
    if not template_folder.is_dir ():
        # the copy keeps the template's own folders; RINT is always present
        template_folder = dest / 'RINT'
    wanted = {f'R{lang}' for lang in args.languages}
    for lang, folder in folders.items ():
        if folder.is_dir ():
            continue
        if not template_folder.is_dir ():
            print (f'::error::no {template_folder.name}/ folder to create R{lang}/ from')
            continue
        folder.mkdir (parents = True, exist_ok = True)
        for grc in sorted (template_folder.glob ('*.grc')):
            text = (template_folder / grc.name).read_text (encoding = 'utf-8-sig')
            text = re.sub (r'/\*\s*[^*]*resources of the[^*]*\*/',
                           f'/* {lang} resources of the {args.name} add-on.\n'
                           f'   TODO: translate every string below - an untranslated copy is not a localization.\n'
                           f'   This folder is compiled when the add-on is built with -DAC_ADDON_LANGUAGE={lang}. */',
                           text, count = 1)
            # keep the UTF-8 BOM of the template: this is how ResConv reads these files here
            (folder / grc.name).write_text (text, encoding = 'utf-8-sig')
        print (f'* created {folder.name}/ from {template_folder.name}/ '
              f'- TRANSLATE its strings, an untranslated copy is not a localization')
    for folder in sorted (dest.glob ('R[A-Z][A-Z][A-Z]')):
        if folder.name == 'RFIX' or folder.name in wanted:
            continue
        shutil.rmtree (folder)
        print (f'* removed {folder.name}/: its language is not in config.json '
              f'(run the script again with --languages to get it back from {template_folder.name}/)')


    problems, notes, leftovers = self_check (dest)
    print ('\n=== self-check ===')
    if problems:
        for problem in problems:
            print (f'PROBLEM: {problem}')
    else:
        print ('* every id used by a .grc is defined in Src/ResourceIds.hpp')
        print ('* every local #include resolves to a real file')
    for note in notes:
        print (f'* note: {note}')
    if leftovers:
        print ('* lines still containing TEST/Test, to review by hand:')
        for line in leftovers:
            print (f'    {line}')
    else:
        print ('* no leftover TEST/Test token')

    tools_sha = ''
    out = run (['git', '-C', str (source), 'ls-files', '-s', 'Tools'])
    if out.returncode == 0:
        match = re.search (r'\b([0-9a-f]{40})\b', out.stdout)
        tools_sha = match.group (1) if match else ''
    url = ''
    gitmodules = dest / '.gitmodules'
    if gitmodules.is_file ():
        url = (re.search (r'url\s*=\s*(\S+)', gitmodules.read_text (encoding = 'utf-8')) or [None, ''])[1]

    if args.init_git or args.create_repo or args.remote_url or args.watch_ci:
        print ('\n=== repository ===')
        prepare_repository (dest, source, args)
        if args.watch_ci:
            print ('\n=== first Actions run ===')
            watch_ci (dest, current_branch (dest))
        return 0

    print ('\n=== next steps ===')
    print (f'  cd "{dest}"')
    if url:
        print (f'  git init -b main')
        print (f'  git submodule add {url} Tools')
        if tools_sha:
            print (f'  git -C Tools checkout {tools_sha} && git add Tools .gitmodules')
    print (f'  git add -A && git commit -m "Start {args.name} from the Archicad add-on template"')
    print ('  create the GitHub repository, then: git remote add origin <url> && git push -u origin main')
    print (f'\nThen check the first Actions run: it must produce '
          + ', '.join (f'{args.name}-AC{v}.apx' for v in args.ac_versions))
    print ('and the "Locate, check and verify the produced .apx" step must list your own resource ids.')
    print ('Import them in Archicad (Options > Add-ons Manager) to test the palette.')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit (main ())
