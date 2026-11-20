#!/usr/bin/env python3
"""Print the add-on identity of a project as GitHub Actions environment lines.

The workflow feeds its results into $GITHUB_ENV so that a project built from
this template never has to repeat its name, its version or its languages in
`.github/workflows/build.yml`: config.json stays the single source of truth
(it is also what Tools/CMakeCommon.cmake reads).
"""

import argparse
import json
import os
import pathlib
import re
import sys

NAME_RE = re.compile (r'^[A-Za-z][A-Za-z0-9_]{0,62}$')


def main ():
    parser = argparse.ArgumentParser (description = 'Export the add-on identity of config.json')
    parser.add_argument ('--config', default = 'config.json', help = 'Path of the add-on config.json')
    parser.add_argument ('--github-env', dest = 'github_env', default = os.environ.get ('GITHUB_ENV', ''),
                         help = 'Optional file to append the variables to (defaults to $GITHUB_ENV)')
    parser.add_argument ('--prefix', default = 'ADDON_', help = 'Prefix of the exported variable names')
    args = parser.parse_args ()

    path = pathlib.Path (args.config)
    if not path.is_file ():
        print (f'::error::{path} does not exist')
        return 1
    config = json.loads (path.read_text (encoding = 'utf-8-sig'))

    errors = []
    for key in ('addOnName', 'defaultLanguage', 'languages', 'version'):
        if key not in config:
            errors.append (f'config.json is missing the key {key!r} required by Tools/CMakeCommon.cmake')
    name = config.get ('addOnName', '')
    if not NAME_RE.match (name or ''):
        errors.append (f'config.json addOnName {name!r} cannot be used as a file name')
    languages = config.get ('languages', [])
    default = config.get ('defaultLanguage', '')
    if default and default not in languages:
        errors.append (f'config.json defaultLanguage {default!r} is not part of languages {languages}')
    if errors:
        for error in errors:
            print (f'::error::{error}')
        return 1

    values = {
        'NAME': name,
        'DEFAULT_LANGUAGE': default,
        'LANGUAGES': ','.join (languages),
        'VERSION': str (config.get ('version', '')),
    }
    for key, value in values.items ():
        line = f'{args.prefix}{key}={value}'
        print (line)
        if args.github_env:
            with open (args.github_env, 'a', encoding = 'utf-8') as env_file:
                env_file.write (line + '\n')
    return 0


if __name__ == '__main__':
    sys.exit (main ())
