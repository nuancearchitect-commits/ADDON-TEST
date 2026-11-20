#!/usr/bin/env python3
"""Verification of a compiled Archicad add-on package (.apx).

An .apx file is a native Windows PE DLL (x64). Its Archicad resources ('STR#',
'GDLG', 'DLGH', 'MDID', ...) are produced by ResConv from the GRC sources of
the add-on and linked into the binary by the Resource Compiler.

The CI workflow uses this script to make sure that a build really produced a
complete, bilingual add-on before the artifact is uploaded.

Hard (fatal) checks:
  * the file exists and is not suspiciously small;
  * it is an x64 PE32+ DLL;
  * every string passed with --expect is found inside it (this proves that
    both the French and the English resources were compiled into the .apx).

Informational checks (reported, never fail the build): the PE resource
directory is walked with a minimal parser, and the resource types/ids found in
the add-on are listed together with the 'MDID' numbers.
"""

import argparse
import hashlib
import pathlib
import re
import struct
import sys

PREDEFINED_TYPES = {
    1: 'CURSOR', 2: 'BITMAP', 3: 'ICON', 4: 'MENU', 5: 'DIALOG', 6: 'STRING',
    7: 'FONTDIR', 8: 'FONT', 9: 'ACCEL', 10: 'RCDATA', 11: 'MESSAGETBL',
    12: 'GROUP_CURSOR', 14: 'GROUP_ICON', 16: 'VERSION', 17: 'DLGINCLUDE',
    19: 'PLUGPLAY', 24: 'ANICURSOR', 25: 'ANIICON', 28: 'HTML',
}

# What the GRC sources of this add-on are expected to produce. The ids come
# from Src/ResourceIds.hpp: 32000 'STR#' (name + description), 32500 'STR#'
# (menu label) and 'MDID', 32530 'STR#' (bilingual UI strings), 32400 'GDLG'
# and 'DLGH' (the palette), 10001 'GICN' (the icon).
# What the GRC sources of this add-on must produce inside the .apx.
# ResConv renames the classic Mac resource types when it writes a Windows
# resource script, so 'STR#' becomes 'STRS' and 'GDLG' becomes 'GSDG'; the
# 'GICN' icon becomes a real Windows icon group whose names contain the source
# file name (see Src/ResourceIds.hpp and RFIX/AddOnFix.grc).
EXPECTED_RESOURCES = {
    'STRS': [32000, 32500, 32530],   # name+description, menu label, palette strings
    'GSDG': [32400],                  # the palette dialog
    'DLGH': [32400],                  # its item handles
    'MDID': [32500],                  # developer id + local id
}

# Types whose ids are strings in the PE resource directory: one id containing
# any of these substrings is enough.
EXPECTED_SUBSTR = {
    'GROUP_ICON': ['I10001'],         # RFIX/Images/AddOnIcon_18x18.svg compiled by ResConv
}


class PEParseError (Exception):
    pass


def safe_text (value) -> str:
    """Always printable: the Windows console of the CI runner uses codepage 1252
    and would raise UnicodeEncodeError on stray surrogates or control characters."""
    text = value if isinstance (value, str) else str (value)
    return text.encode ('utf-8', 'backslashreplace').decode ('utf-8', 'replace')


def read_header (data: bytes):
    """Parse what is needed to locate the PE resource tree.

    Returns (machine, magic, characteristics, sections, resource_rva, resource_size)
    with sections = [(name, virtual_address, virtual_size, raw_ptr, raw_size), ...].
    """
    if len (data) < 0x40 or data[:2] != b'MZ':
        raise PEParseError ('not an MZ/PE file')
    e_lfanew = struct.unpack_from ('<I', data, 0x3C)[0]
    if data[e_lfanew:e_lfanew + 4] != b'PE\0\0':
        raise PEParseError ('missing PE signature')
    machine, num_sections, _, _, _ = struct.unpack_from ('<HHHHI', data, e_lfanew + 4)
    size_of_optional_header = struct.unpack_from ('<H', data, e_lfanew + 20)[0]
    characteristics = struct.unpack_from ('<H', data, e_lfanew + 22)[0]
    magic = struct.unpack_from ('<H', data, e_lfanew + 24)[0]
    sections = []
    section_base = e_lfanew + 24 + size_of_optional_header
    for index in range (num_sections):
        entry = section_base + index * 40
        if entry + 40 > len (data):
            raise PEParseError ('section table out of bounds')
        name = data[entry:entry + 8].rstrip (b'\0').decode ('latin-1')
        virtual_size, virtual_address, raw_size, raw_ptr = struct.unpack_from ('<IIII', data, entry + 8)
        sections.append ((name, virtual_address, virtual_size, raw_ptr, raw_size))
    resource_rva = resource_size = 0
    # The resource directory is data directory entry 2, right after the standard
    # fields of the optional header (112 bytes for PE32+, 96 for PE32).
    data_directories = e_lfanew + 24 + (112 if magic == 0x20B else 96)
    if data_directories + 3 * 8 <= len (data):
        resource_rva, resource_size = struct.unpack_from ('<II', data, data_directories + 2 * 8)
    return machine, magic, characteristics, sections, resource_rva, resource_size


class RvaMapper:
    """Converts a relative virtual address into an offset inside the file on disk.

    Note that the PE *resource directory* offsets are NOT RVAs: they are
    offsets relative to the start of the resource directory (see
    walk_resources), only IMAGE_RESOURCE_DATA_ENTRY.OffsetToData is an RVA.
    """

    def __init__ (self, data: bytes, sections):
        self.data = data
        self.sections = sections

    def offset_of (self, rva: int) -> int:
        for _, virtual_address, virtual_size, raw_ptr, raw_size in self.sections:
            span = max (raw_size, virtual_size)
            if raw_ptr and virtual_address <= rva < virtual_address + span:
                return raw_ptr + (rva - virtual_address)
        if 0 < rva < len (self.data):
            return rva          # offsets already relative to the file start
        raise PEParseError (f'RVA 0x{rva:x} is not covered by any section')

    def describe (self):
        parts = []
        for name, virtual_address, _, raw_ptr, raw_size in self.sections:
            parts.append (f'{name}: rva=0x{virtual_address:x} raw=0x{raw_ptr:x} size=0x{raw_size:x}')
        return '; '.join (parts)


def directory_entries (data: bytes, offset: int, resolve, what: str):
    if offset < 0 or offset + 16 > len (data):
        raise PEParseError (f'{what}: directory at file offset 0x{offset:x} is outside the file '
                            f'(size 0x{len (data):x})')
    # IMAGE_RESOURCE_DIRECTORY: Characteristics, TimeDateStamp, MajorVersion,
    # MinorVersion, NumberOfNamedEntries, NumberOfIdEntries  (16 bytes)
    directory_header = struct.unpack_from ('<IIHHHH', data, offset)
    named_count, id_count = directory_header[4], directory_header[5]
    if named_count + id_count > 4096:
        raise PEParseError (f'{what}: implausible entry count ({named_count} named, {id_count} by id)')
    entries = []
    base = offset + 16
    for index in range (named_count + id_count):
        entry = base + index * 8
        if entry + 8 > len (data):
            raise PEParseError (f'{what}: entry {index} is outside the file')
        name_or_id, sub = struct.unpack_from ('<II', data, entry)
        if name_or_id & 0x80000000:
            name_offset = resolve (name_or_id)
            length = struct.unpack_from ('<H', data, name_offset)[0]
            label = safe_text (data[name_offset + 2:name_offset + 2 + length * 2].decode ('utf-16-le', 'replace'))[:32]
        else:
            label = name_or_id
        entries.append ((label, sub))
    return entries


def walk_resources (data: bytes, mapper: RvaMapper, resource_rva: int, log = None):
    """Return ({type name: [(id, size, rva), ...]}, [parse problem, ...]).

    Every level is parsed defensively: a type that cannot be walked is reported
    as a problem instead of losing the whole tree (this is a diagnostic helper,
    not a PE library).
    """
    if not resource_rva:
        rsrc = next ((s for s in mapper.sections if s[0] == '.rsrc'), None)
        if rsrc is None:
            raise PEParseError ('no resource data directory and no .rsrc section')
        resource_rva = rsrc[1]

    problems = []
    resources = {}
    root_offset = mapper.offset_of (resource_rva)
    named_count, id_count = struct.unpack_from ('<HH', data, root_offset + 12)
    if log:
        log (f'* resource root: file offset 0x{root_offset:x} (rva 0x{resource_rva:x}), '
             f'{named_count} named type(s) + {id_count} type(s) by id')

    # Inside the resource directory the offsets of the tree (sub-directories and
    # type/id name strings) are relative to the start of the root directory, not
    # image RVAs. Only the data entries hold an image RVA.
    def resolve (value: int) -> int:
        """Resolve the offset of a sub-directory or of a type/id name string.

        Those offsets are stored relative to the start of the resource directory
        (that is how rc.exe writes them); a value that cannot be read that way is
        resolved through the section table instead, so a slightly different
        convention never breaks the walk."""
        value &= 0x7FFFFFFF
        candidate = root_offset + value
        if 0 <= candidate and candidate + 16 <= len (data):
            return candidate
        return mapper.offset_of (value)

    def resolve_data (value: int) -> int:
        """Resolve IMAGE_RESOURCE_DATA_ENTRY.OffsetToData, which is an image RVA."""
        value &= 0x7FFFFFFF
        try:
            return mapper.offset_of (value)
        except PEParseError:
            return root_offset + value

    for type_label, type_sub in directory_entries (data, root_offset, resolve, 'resource type directory'):
        key = type_label if isinstance (type_label, str) else PREDEFINED_TYPES.get (type_label, f'#{type_label}')
        if not type_sub & 0x80000000:
            problems.append (f'{key}: entry does not point to a directory')
            continue
        try:
            id_entries = directory_entries (data, resolve (type_sub), resolve,
                                            f'resource type {key} directory')
        except PEParseError as error:
            problems.append (safe_text (f'{key}: {error}'))
            continue
        for res_id, res_sub in id_entries:
            if not res_sub & 0x80000000:
                problems.append (f'{key}/{res_id}: entry does not point to a directory')
                continue
            try:
                lang_entries = directory_entries (data, resolve (res_sub), resolve,
                                                   f'{key} id {res_id} directory')
            except PEParseError as error:
                problems.append (safe_text (f'{key}/{res_id}: {error}'))
                continue
            for _, lang_entry in lang_entries:
                if lang_entry & 0x80000000:
                    problems.append (f'{key}/{res_id}: unexpected nested directory')
                    continue
                try:
                    res_rva, res_size = struct.unpack_from ('<II', data, resolve_data (lang_entry))
                except (PEParseError, struct.error) as error:
                    problems.append (safe_text (f'{key}/{res_id}: {error}'))
                    continue
                resources.setdefault (key, []).append ((res_id, res_size, res_rva))
    return resources, problems


# --- automatic discovery of what the add-on sources declare -------------------
#
# These helpers let the CI verify *any* add-on built on this template without
# repeating the resource ids and the UI strings inside the workflow: they are
# read back from the sources themselves (Src/ResourceIds.hpp + the .grc files).

WINDOWS_TYPE_NAMES = {
    'STR#': ['STRS', 'STR#'],          # ResConv renames the Mac type names on Windows
    'GDLG': ['GSDG', 'GDLG'],
    'GICN': ['GROUP_ICON', 'ICON'],
}

TYPE_LINE_RE = re.compile (r"^\s*'([A-Za-z0-9#]{1,4})'\s+(\d+|[A-Za-z_][A-Za-z0-9_]*)")
DEFINE_RE = re.compile (r'^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(0[xX][0-9a-fA-F]+|\d+)\s*(?:/.*)?$')
STRING_RE = re.compile (r'"((?:[^"\\\n]|\\.)*)"')


def read_defines (path: pathlib.Path):
    """The #define id map of the add-on (also seen by ResConv, which preprocesses the .grc)."""
    if not path.is_file ():
        return {}
    defines = {}
    for line in path.read_text (encoding = 'utf-8-sig', errors = 'replace').split ('\n'):
        match = DEFINE_RE.match (line)
        if match:
            defines[match.group (1)] = int (match.group (2), 0)
    return defines


def parse_grc_files (grc_paths, defines):
    """Return ({type: {ids}}, {type: {id: [strings]}}) of the given .grc files.

    Only the quoted strings *inside* a 'STR#' body are considered UI strings:
    they are the ones ResConv writes verbatim into the STRS resource.
    """
    resources = {}
    strings = {}
    for grc in grc_paths:
        if not grc.is_file ():
            continue
        current_type = None
        current_id = None
        depth = 0
        for raw_line in grc.read_text (encoding = 'utf-8-sig', errors = 'replace').split ('\n'):
            line = re.sub (r'/\*.*?\*/', '', raw_line)
            if depth == 0:
                match = TYPE_LINE_RE.match (line)
                if not match:
                    continue
                current_type = match.group (1)
                name = match.group (2)
                current_id = int (name, 0) if name[0].isdigit () else defines.get (name, None)
                if current_id is None:
                    current_type = None
                    continue
                resources.setdefault (current_type, set ()).add (current_id)
                depth = line.count ('{') - line.count ('}')
                continue
            stripped = line.strip ()
            if current_type == 'STR#':
                for text in STRING_RE.findall (line):
                    cleaned = text.strip ()
                    if len (cleaned) >= 4 and not re.search (r'[\^%]', cleaned):
                        strings.setdefault ((current_type, current_id), []).append (cleaned)
            depth += line.count ('{') - line.count ('}')
            if depth <= 0:
                depth = 0
                current_type = None
    return resources, strings


def discover (project_dir: pathlib.Path, language: str):
    """Read the add-on sources: ids, resource types and UI strings to expect."""
    project_dir = pathlib.Path (project_dir)
    defines = read_defines (project_dir / 'Src' / 'ResourceIds.hpp')
    grc_paths = sorted ((project_dir / 'RFIX').glob ('*.grc'))
    if language:
        grc_paths += sorted ((project_dir / ('R' + language)).glob ('*.grc'))
    resources, strings = parse_grc_files (grc_paths, defines)

    mdid = []
    for grc in grc_paths:
        text = grc.read_text (encoding = 'utf-8-sig', errors = 'replace')
        match = re.search (r"'MDID'\s+\d+[^{}]*\{\s*(\d+)\D+(\d+)", text)
        if match:
            mdid = [int (match.group (1)), int (match.group (2))]
            break
    return resources, strings, mdid, [str (p.relative_to (project_dir)) for p in grc_paths]


def find_needle (blob: bytes, text: str):
    """Find a UI string the way ResConv stores it on Windows (codepage 1252),
    falling back to UTF-16LE and UTF-8."""
    for encoding in ('cp1252', 'utf-16-le', 'utf-8'):
        try:
            needle = text.encode (encoding)
        except UnicodeEncodeError:
            continue
        position = blob.find (needle)
        if position != -1:
            return encoding, position
    return None, -1


def main ():
    parser = argparse.ArgumentParser (description = 'Verify a compiled Archicad .apx file.')
    parser.add_argument ('apx', help = 'Path of the .apx file to check')
    parser.add_argument ('--expect', action = 'append', default = [],
                         help = 'A UI string that must be present in the add-on (repeatable)')
    parser.add_argument ('--mdid', action = 'append', type = int, default = [],
                         help = 'A Graphisoft MDID number expected in the add-on (repeatable, informational)')
    parser.add_argument ('--mdid-from-grc', dest = 'mdid_from_grc',
                         help = 'GRC file holding the \'MDID\' resource; its two numbers are used as --mdid values')
    parser.add_argument ('--min-size', type = int, default = 4096,
                         help = 'Minimum accepted size in bytes (default: 4096)')
    parser.add_argument ('--report', help = 'Optional file receiving a markdown report')
    parser.add_argument ('--auto-from', dest = 'auto_from', metavar = 'PROJECT_DIR',
                         help = 'Discover the expected resources and UI strings from the add-on sources '
                                '(Src/ResourceIds.hpp + RFIX/*.grc + R<language>/*.grc) instead of '
                                'repeating them on the command line')
    parser.add_argument ('--language', default = '',
                         help = 'Language folder compiled by this build (e.g. INT); its strings are '
                                'expected too when --auto-from is used')
    args = parser.parse_args ()

    path = pathlib.Path (args.apx)
    lines = []
    failures = []

    if args.auto_from:
        resources_expected, strings_expected, mdid, used = discover (pathlib.Path (args.auto_from), args.language)
        EXPECTED_RESOURCES.clear ()
        EXPECTED_SUBSTR.clear ()
        for label, ids in sorted (resources_expected.items (), key = lambda item: str (item[0])):
            for res_id in sorted (ids):
                if label == 'GICN':
                    # ResConv turns 'GICN' + the SVG into real Windows icon groups whose
                    # names contain the GICN id (I10001&96, I10001&192, ...&D for dark mode).
                    EXPECTED_SUBSTR.setdefault ('GROUP_ICON', []).append (str (res_id))
                    continue
                EXPECTED_RESOURCES.setdefault (label, []).append (res_id)
        for (label, res_id), texts in strings_expected.items ():
            for text in texts:
                if text not in args.expect:
                    args.expect.append (text)
        if mdid and not args.mdid:
            args.mdid = mdid
        print (f'* discovered from {args.auto_from} (language {args.language or "default"}):')
        print (f'    .grc files: {", ".join (used) or "none"}')
        print (f'* expected resources: '
               + ', '.join (f'{name} {sorted (ids)}' for name, ids in sorted (EXPECTED_RESOURCES.items (), key = lambda i: str (i[0]))))
        print (f'* expected UI strings: {len (args.expect)}')
        if args.mdid:
            print (f'* expected MDID numbers: {args.mdid}')
        print ('')

    def say (text):
        text = safe_text (text)
        lines.append (text)
        print (text)

    def fail (text):
        text = safe_text (text)
        failures.append (text)
        print (f'::error::{text}')

    if not path.is_file ():
        fail (f'{path} does not exist - no add-on was produced')
    else:
        data = path.read_bytes ()
        say (f'* File `{path.name}`: {len (data)} bytes')
        say (f'* SHA-256: `{hashlib.sha256 (data).hexdigest ()}`')
        if len (data) < args.min_size:
            fail (f'{path.name} is smaller than {args.min_size} bytes - empty or truncated add-on')

        try:
            machine, magic, characteristics, sections, resource_rva, resource_size = read_header (data)
            names = {0x8664: 'x64 (AMD64)', 0x14C: 'x86 (i386)', 0xAA64: 'ARM64'}
            say (f'* PE machine: {names.get (machine, hex (machine))}, format: {"PE32+ (64 bit)" if magic == 0x20B else hex (magic)}, '
                 f'dll flag: {bool (characteristics & 0x2000)}, sections: {len (sections)}')
            say (f'* sections: {", ".join (s[0] for s in sections) or "none"}')
            if machine != 0x8664:
                fail ('the add-on is not an x64 binary')
            if magic != 0x20B:
                fail ('the add-on is not a PE32+ image')
            if not characteristics & 0x2000:
                fail ('the add-on is not marked as a DLL')

            for text in args.expect:
                encoding, position = find_needle (data, text)
                if position == -1:
                    fail (f'UI string not found in the add-on: {text!r}')
                else:
                    say (f'* language check: {text!r} found ({encoding}, offset {position})')

            for number in args.mdid:
                packed = struct.pack ('<I', number & 0xFFFFFFFF)
                say (f'* MDID check: {number} {"found" if packed in data else "not found as raw UInt32 bytes"} '
                     f'(informational)')
            if len (args.mdid) >= 2:
                pair = struct.pack ('<II', args.mdid[0] & 0xFFFFFFFF, args.mdid[1] & 0xFFFFFFFF)
                say (f'* MDID check: developer id + local id stored back to back: {"found" if pair in data else "not found (layout may differ)"} '
                     f'(informational)')

            resources = None
            walk_problems = []
            try:
                mapper = RvaMapper (data, sections)
                say (f'* .rsrc: data directory rva=0x{resource_rva:x} size=0x{resource_size:x}')
                resources, walk_problems = walk_resources (data, mapper, resource_rva, say)
            except PEParseError as error:
                walk_problems = [safe_text (f'resource tree not parsed: {error}')]
            except Exception as error:                                # noqa: BLE001 - diagnostics must not break CI
                walk_problems = [safe_text (f'resource tree not parsed: unexpected error {error!r}')]
            for problem in walk_problems[:8]:
                say (f'* resource walk: {problem}')
            if len (walk_problems) > 8:
                say (f'* resource walk: {len (walk_problems) - 8} more problem(s) not shown')

            if resources is not None and not resources:
                say ('* no resource could be listed by the PE walk (informational: the build '
                     'already ran ResConv, and the string checks are the authoritative ones)')
            if resources:
                say (f'* resources found in the add-on ({len (resources)} type/labels):')
                for label in sorted (resources, key = str):
                    label_entries = resources[label]
                    ids = sorted ({entry[0] for entry in label_entries}, key = str)
                    say (f'    * {label}: {len (label_entries)} data entry/entries, ids {ids[:16]}')
                summary_parts = []
                for label, entries in sorted (resources.items (), key = lambda item: str (item[0])):
                    ids = sorted ({entry[0] for entry in entries}, key = str)[:12]
                    summary_parts.append (f'{label} ({len (entries)} entries, ids {ids})')
                say ('* resource summary: ' + ', '.join (summary_parts))
                for label, expected_ids in EXPECTED_RESOURCES.items ():
                    # ResConv may rename a Mac type name for the Windows resource directory.
                    pe_names = WINDOWS_TYPE_NAMES.get (label, [label])
                    found_name = None
                    present = set ()
                    for name in pe_names:
                        if name in resources:
                            found_name = name
                            present |= {entry[0] for entry in resources[name]}
                    missing = [res_id for res_id in expected_ids if res_id not in present]
                    if found_name and found_name != label:
                        say (f'* resource check: {label} is stored as the {found_name} type '
                             f'(ResConv naming)')
                    if missing and not walk_problems:
                        fail (f'resource check: {label} missing id(s) {missing} - the GRC resource '
                              f'was not compiled into this add-on')
                    elif missing:
                        say (f'* resource check: {label} missing id(s) {missing} (informational)')
                    else:
                        say (f'* resource check: {label} id(s) {expected_ids} present')
                for label, needles in EXPECTED_SUBSTR.items ():
                    present_ids = [str (entry[0]) for entry in resources.get (label, [])]
                    hit = [needle for needle in needles
                           if any (needle in res_id for res_id in present_ids)]
                    missing_needles = [needle for needle in needles if needle not in hit]
                    if not missing_needles:
                        say (f'* resource check: {label} present for {", ".join (hit)}')
                    elif not walk_problems:
                        fail (f'resource check: {label} has no id containing {missing_needles} - the icon '
                              f'resource was not compiled into this add-on')
                    else:
                        say (f'* resource check: {label} has no id containing {missing_needles} (informational)')
            else:
                say ('* resource tree walk interrupted, falling back to a byte scan')
                # Fallback: the resource type names are stored as UTF-16LE strings
                # in the PE resource directory, so their presence shows that the
                # resources compiled by ResConv were linked into the add-on.
                type_names = sorted (set (list (EXPECTED_RESOURCES) + list (EXPECTED_SUBSTR)))
                present = [name for name in type_names if name.encode ('utf-16-le') in data]
                missing = [name for name in type_names if name not in present]
                say (f'* resource types found (UTF-16LE scan): {", ".join (present) or "none"}')
                if missing:
                    say (f'* resource types not detected: {", ".join (missing)} (informational)')

        except PEParseError as error:
            fail (f'not a readable PE file: {error}')
        except Exception as error:                                # noqa: BLE001 - diagnostics must not break CI
            say (f'* PE analysis stopped on unexpected error: {error!r} (informational)')

    print ('')
    if failures:
        for failure in failures:
            print (f'FAIL: {safe_text (failure)}')
    else:
        print ('OK: the .apx contains the expected bilingual resources')

    if args.report:
        report = lines + ([] if not failures else [''] + [f'* PROBLEM: {f}' for f in failures])
        pathlib.Path (args.report).write_text ('\n'.join (report) + '\n', encoding = 'utf-8')

    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit (main ())
