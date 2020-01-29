#!/usr/bin/env python3

"""Scan the dependencies for licenses and produce a report.

   Dependencies
   ------------
   ninka - Program used to classify license-like files. We don't automatically
    install this. See http://ninka.turingmachine.org for more information.

   Notes
   -----
   The license JSON used by this is based on the one defined in the GitHub project
   jk1/Gradle-License-Report, but with a few fields added.

   The fields we will populate are as follows:

    moduleName: The name of the prerequisite module.
    moduleVersion: The version, if it can be determined.
    moduleLicense: The name of the license type, standardized if possible. Will be
        set to 'Unknown' if we cannot determine it automatically.
    moduleUrl: Identifies the source of the module.
    moduleLicenseUrl: The URL of the license specific to the module, if we can
        determine that information. Typically this will not be provided unless
        added manually.

   The added fields are as follows:

    x-usedBy: Will list the prerequisites that use this module.
    x-spdxId: If the license is recognized in the SPDX database, this is the id.
    x-isOsiApproved: Will be true if the SPDX database marks this as approved.

    The following fields are not added by this module, but may be manually added and
    relate to the operation of the module.

    x-manuallyEdited: Set this to true to mark a manual entry in the file. Use this
        to handle the cases that we cannot deal with automatically. The scanner will
        always include the manually edited entries without change except for adding
        to the x-usedBy list.
    x-comments: Not actually used by this package but we recommend adding this field
        if you set x-manuallyEdited to true in order to explain why the license is
        considered acceptable.
"""

import argparse
import bisect
import json
import logging
import os
import urllib.parse
import subprocess
import sys

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

import requests


_PREREQS_DIRECTORY = '.prereqs/Darwin-x86_64'
_PREREQS_LICENSE_FILE = 'Dependencies/prereqs-licenses.json'
_PREREQS_FILE = 'Dependencies/prereqs.json'
_SPDX_LICENSES = 'BuildSystem/common/spdx-licenses.json'


# MARK: Local Utilities

def _process(command: str):
    logging.debug("Processing command: %s", command)
    res = subprocess.Popen("%s" % command, shell=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return res.stdout

def _get_run(command: str, directory: str = None):
    logging.debug("Running command: %s", command)
    res = subprocess.run("%s" % command, shell=True, check=True, cwd=directory,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return res.stdout.decode('utf-8').strip()

def _get_license_filename(dirname: str):
    try:
        for entry in os.listdir(dirname):
            if entry.upper().startswith('LICENSE'):
                return entry
    except FileNotFoundError:
        pass
    return None

def _read_file_contents(filename: str) -> str:
    with open(filename, 'r') as file:
        data = file.read().replace('\n', '')
    return data.strip()

# Note that this will return either a List or a Dict depending on the contents
# of the JSON file.
def _read_json_file(filename: str):
    logging.debug("Reading %s as JSON", filename)
    with open(filename) as infile:
        return json.load(infile)

def _get(url: str):
    assert bool(url), 'Must define a URL'
    logging.debug("GET %s", url)
    resp = requests.get(url, headers={'Accept': 'application/json'})
    if not (resp.status_code >= 200 and resp.status_code < 300):
        raise RuntimeError("GET of %s did not return an OK response" % url)
    ctype = resp.headers.get('content-type', '')
    if not ctype.startswith('application/json'):
        raise RuntimeError("GET of %s did not claim to be 'application/json'" % url)
    return resp.json()


# pylint: disable=missing-function-docstring
#   Justification: we don't need docstrings on the methods in a private class.
class _SPDX:
    _ninka_fallbacks = {
        'spdxBSD3': 'BSD-3-Clause',
        'Apache-2': 'Apache-2.0'
    }

    def __init__(self, filename: str):
        entries = {}
        name_map = {}
        logging.info("Reading SPDX entries from %s", filename)
        for lic in _read_json_file(filename)['licenses']:
            entries[lic['licenseId']] = lic
            name_map[lic['name']] = lic['licenseId']
        self._entries = entries
        self._name_map = name_map

    def get_entry(self, licenseid: str) -> Dict:
        return self._entries.get(licenseid, None)

    def search(self, srch: str) -> Dict:
        entry = self.get_entry(srch)
        if not entry:
            entry = self._try_name_search(srch)
            if not entry:
                entry = self._try_ninka_overrides(srch)
        if entry:
            logging.debug("  SPDX identified '%s' as '%s' (id='%s')",
                          srch,
                          entry['name'],
                          entry['licenseId'])
        return entry

    @classmethod
    def set_into_license(cls, entry: Dict, lic: Dict):
        lic['moduleLicense'] = entry['name']
        lic['x-spdxId'] = entry['licenseId']
        lic['x-isOsiApproved'] = entry['isOsiApproved']

    def _try_name_search(self, name: str) -> Dict:
        licenseid = self._name_map.get(name, None)
        if licenseid:
            return self.get_entry(licenseid)
        return None

    def _try_ninka_overrides(self, name: str) -> Dict:
        licenseid = self._ninka_fallbacks.get(name, None)
        if licenseid:
            return self.get_entry(licenseid)
        if name.startswith('spdx'):
            return self.get_entry(name[4:])
        return None


# pylint: disable=too-few-public-methods
#   Justification: There is only one feasible method and we wish to retain state hence
#                  the need for the class.
class _GitHubAPI:
    def __init__(self):
        self._cached = {}
        self._remaining_calls = -1

    def lookup(self, url: str) -> str:
        host, organization, project = self._parse_url(url)
        if project.endswith('.git'):
            project = project[:-4]
        if organization in self._cached:
            return self._license_from_entry(self._cached[organization], project)
        if host == 'github.com':
            logging.info("   Looking up '%s' in github", url)
            projects = self._try_api('orgs', organization)
            if projects is None:
                projects = self._try_api('users', organization)
            if projects is not None:
                self._cached[organization] = projects
                return self._license_from_entry(projects, project)
        return None

    def _try_api(self, key: str, organization: str) -> List:
        if self._can_call_github():
            try:
                return _get("https://api.github.com/%s/%s/repos" % (key, organization))
            # pylint: disable=broad-except
            #   Justification: We really do want to trap all user defined exceptions.
            except Exception:
                pass
        return None

    @classmethod
    def _parse_url(cls, url):
        host = None
        organization = None
        project = None
        if url:
            parsed_url = urllib.parse.urlparse(url)
            host = parsed_url.netloc
            parts = parsed_url.path.split('/')
            for i, part in enumerate(parts):
                part = parts[i]
                if part == '':
                    continue
                if organization is None:
                    organization = part
                    continue
                if project is None:
                    project = part
                    break
        return host, organization, project

    def _can_call_github(self) -> bool:
        try:
            if self._remaining_calls == -1:
                result = _get("https://api.github.com/rate_limit")
                self._remaining_calls = result['rate']['remaining']
            logging.debug("  GitHub API calls remaining: %d", self._remaining_calls)
            if self._remaining_calls > 0:
                self._remaining_calls -= 1
                return True
            return False
        # pylint: disable=broad-except
        #   Justification: We really do want to trap all user defined exceptions.
        except Exception as ex:
            logging.warning("%s", ex)
            return False

    @classmethod
    def _license_from_entry(cls, projects: List, project_name: str) -> str:
        for project in projects:
            if project.get('name', '') == project_name:
                lic = project.get('license', {})
                lic_name = lic.get('spdx_id', None)
                if lic_name:
                    logging.debug("  Github identified license as '%s'", lic_name)
                return lic_name
        return None



# MARK: Scanner Infrastructure

class Scanner(ABC):
    """Base class defining the scanning API and providing common scanning helper methods."""

    spdx = None
    _github = None

    def __init__(self):
        if not Scanner._github:
            Scanner._github = _GitHubAPI()
        if not Scanner.spdx:
            Scanner.spdx = _SPDX(_SPDX_LICENSES)

    @abstractmethod
    def should_scan(self) -> bool:
        """Subclasses must override this to return True if this scanner is suitable for
           the current project. You may also assume that if it returns True then scan()
           will be called, and you can safely save any state needed by should_scan() to be
           reused by scan().
        """
        raise NotImplementedError()

    @abstractmethod
    def scan(self) -> List:
        """Subclasses must override this to return a List of license entries that should
           be recorded for the current project. You may assume that should_scan() has been
           called and has returned True.
        """
        raise NotImplementedError()

    @classmethod
    def guess_license_with_ninka(cls, filename: str) -> str:
        """Given a filename, use ninka to try to determine the license type."""
        licensetype = _get_run("ninka %s | cut -d ';' -f2" % filename)
        logging.debug("  Ninka identified license as '%s'", licensetype)
        entry = cls.spdx.search(licensetype)
        if entry:
            licensetype = entry['name']
        return licensetype

    @classmethod
    def ensure_used_by(cls, modulename: str, lic: Dict):
        """Ensure that the given modulename is in the usedBy field and in the correct order.
        """
        if 'x-usedBy' in lic:
            if modulename not in lic['x-usedBy']:
                bisect.insort(lic['x-usedBy'], modulename)
        else:
            lic['x-usedBy'] = [modulename]

    def add_licenses(self, modulename: str, licenses: Dict):
        """Calls should_scan() and scan() and adds the results to licenses."""
        if self.should_scan():
            logging.info("Running the scanner '%s'", type(self).__name__)
            new_licenses = self.scan()
            self._adjust_and_add_new_licenses(modulename, new_licenses, licenses)

    def _adjust_and_add_new_licenses(self, modulename: str, new_licenses: Dict, licenses: Dict):
        for lic in new_licenses:
            key = lic['moduleName']
            if key in licenses:
                if self._should_add_to_used_by(lic):
                    self.ensure_used_by(modulename, licenses[key])
                logging.info("   Entry '%s' already exists", lic['moduleName'])
            else:
                if self._should_add_to_used_by(lic):
                    self.ensure_used_by(modulename, lic)
                entry = self.spdx.search(lic['moduleLicense'])
                if entry:
                    self.spdx.set_into_license(entry, lic)
                else:
                    licenseid = self._github.lookup(lic.get('moduleUrl', None))
                    if licenseid:
                        entry = self.spdx.get_entry(licenseid)
                        if entry:
                            self.spdx.set_into_license(entry, lic)
                licenses[key] = lic
                logging.info("   Added '%s' as '%s'",
                             lic['moduleName'],
                             lic['moduleLicense'])

    @classmethod
    def _should_add_to_used_by(cls, lic: Dict) -> bool:
        return 'x-usedBy' not in lic


class ManuallyEditedScanner(Scanner):
    """Scanner that adds any existing items that have been manually edited."""

    def __init__(self):
        super().__init__()
        self._entries = None

    def should_scan(self) -> bool:
        if os.path.isfile(_PREREQS_LICENSE_FILE):
            entries = []
            for dep in _read_json_file(_PREREQS_LICENSE_FILE)['dependencies']:
                if dep.get('x-manuallyEdited', False):
                    entries.append(dep)
            self._entries = entries
        return bool(self._entries)

    def scan(self) -> List:
        if self._entries:
            logging.info("   found %s", [sub['moduleName'] for sub in self._entries])
        return self._entries


class DirectoryBasedScanner(Scanner):
    """Base class for scanners that are based on an already checked out source directory."""

    def __init__(self):
        super().__init__()
        self._entries = None

    def scan(self) -> List:
        lics = {}
        entries = self.get_project_list()
        for prereq in entries:
            logging.info("   ...examining '%s'", prereq['name'])
            self._process_prereq(prereq, lics)
        return lics.values()

    def get_project_list(self) -> List:
        """Subclasses must override this to return a list of dictionary objects.

        Each object in the returned list should have the following members:
          name: a string containing the project name
          directory: a string providing where the directory exists
          version (optional): a string containing the project version
          url (optional): a string providing the project URL

        Note that this will only be called if should_scan() returns True.
        """
        raise NotImplementedError()

    @classmethod
    def _process_prereq(cls, prereq: Dict, licenses: List):
        details = cls._details_for_prereq(prereq)
        other_licenses = details['otherLicenses']
        if other_licenses:
            logging.info("      also found %s", [sub['moduleName'] for sub in other_licenses])
            for lic in other_licenses:
                if lic['moduleName'] in licenses:
                    cls.ensure_used_by(prereq['name'], licenses[lic['moduleName']])
                else:
                    licenses[lic['moduleName']] = lic
        lic = cls._license_from_details(details)
        assert lic['moduleName'] not in licenses
        licenses[lic['moduleName']] = lic

    @classmethod
    def _details_for_prereq(cls, entry: Dict) -> Dict:
        details = entry.copy()
        directory = entry['directory']
        details['otherLicenses'] = cls._get_other_licenses(directory)
        details['license'] = 'Unknown'
        if directory is not None and os.path.isdir(directory):
            filename = "%s/%s" % (directory, _get_license_filename(directory))
            if os.path.isfile(filename):
                details['license'] = cls.guess_license_with_ninka(filename)
        return details

    @classmethod
    def _get_other_licenses(cls, directory: str) -> List:
        filename = "%s/%s" % (directory, _PREREQS_LICENSE_FILE)
        if os.path.isfile(filename):
            return _read_json_file(filename)['dependencies']
        return None

    @classmethod
    def _license_from_details(cls, details: Dict) -> Dict:
        lic = {'moduleName': details['name']}
        if details['version']:
            lic['moduleVersion'] = details['version']
        if details['url']:
            lic['moduleUrl'] = details['url']
        lic['moduleLicense'] = 'Unknown' if not details['license'] else details['license']
        return lic


class KSSPrereqScanner(DirectoryBasedScanner):
    """Scanner that examines the git and tarball prerequisites in the project."""

    def should_scan(self) -> bool:
        return os.path.isfile(_PREREQS_FILE)

    def get_project_list(self) -> List:
        try:
            prereqs = []
            for entry in _read_json_file(_PREREQS_FILE):
                if 'git' in entry:
                    prereqs.append(self._prereq_for_git_entry(entry))
                if 'tarball' in entry:
                    prereqs.append(self._prereq_for_tarball_entry(entry))
            return prereqs
        except FileNotFoundError:
            return None

    @classmethod
    def _prereq_for_git_entry(cls, entry: Dict) -> Dict:
        url = entry['git']
        name = os.path.basename(urllib.parse.urlparse(url).path)
        if name.endswith('.git'):
            name = name[:-4]
        directory = "%s/%s" % (_PREREQS_DIRECTORY, name)
        version = None
        filename = "%s/REVISION" % directory
        if os.path.isfile(filename):
            version = _read_file_contents(filename)
        return {'name': name, 'version': version, 'directory': directory, 'url': url}

    @classmethod
    def _prereq_for_tarball_entry(cls, entry: Dict) -> Dict:
        url = entry['tarball']
        filename = entry.get('filename', None)
        if not filename:
            filename = os.path.basename(urllib.parse.urlparse(url).path)
        (name, version, directory) = cls._parse_tarball_name(filename)
        return {'name': name, 'version': version, 'directory': directory, 'url': url}

    @classmethod
    def _parse_tarball_name(cls, filename: str) -> Tuple:
        name = filename
        if name.endswith('.tar.gz'):
            name = name[:-7]
        directory = "%s/%s" % (_PREREQS_DIRECTORY, name)
        parts = name.split('-', 1)
        name = parts[0]
        version = None if len(parts) == 1 else parts[1]
        return (name, version, directory)


class SwiftModuleScanner(DirectoryBasedScanner):
    """Scanner that examines swift module prerequisites."""

    def __init__(self):
        super().__init__()
        self._files = None

    def should_scan(self) -> bool:
        self._files = self._get_xcode_package_dependency_files()
        return bool(self._files)

    def get_project_list(self) -> List:
        projects = {}
        for filename in self._files:
            logging.info("   ...examining '%s'", filename)
            entries = self._get_entries_for_xcode_package_dependency_file(filename)
            logging.info("      found %s", sorted([sub['name'] for sub in entries]))
            for entry in entries:
                key = entry['name']
                if key not in projects:
                    projects[key] = entry
        return sorted(projects.values(), key=lambda x: x['name'])

    @classmethod
    def _get_xcode_package_dependency_files(cls) -> List:
        files = []
        for line in _process('find . -name Package.resolved'):
            files.append(line.decode('utf-8').rstrip())
        return files

    @classmethod
    def _get_entries_for_xcode_package_dependency_file(cls, filename: str) -> List:
        entries = []
        for pin in _read_json_file(filename)['object']['pins']:
            name = pin['package']
            entry = {
                'name': name,
                'version': pin['state'].get('version', None),
                'directory': cls._get_project_directory(name),
                'url': pin.get('repositoryURL', None)
            }
            entries.append(entry)
        return entries

    @classmethod
    def _get_project_directory(cls, name: str) -> str:
        deriveddata = os.path.expanduser("~/Library/Developer/Xcode/DerivedData")
        if os.path.isdir(deriveddata):
            for line in _process("find %s -type d -name %s" % (deriveddata, name)):
                line = line.decode('utf-8').rstrip()
                if os.path.isdir(line):
                    return line
        logging.warning("Could not find the source directory for %s", name)
        return None


class PipScanner(Scanner):
    """Scanner that looks for pip prerequisites in the project."""

    def __init__(self):
        super(PipScanner, self).__init__()
        self._pips = None

    def should_scan(self) -> bool:
        if os.path.isfile(_PREREQS_FILE):
            self._load_pip_prerequisites()
        return bool(self._pips)

    def scan(self) -> List:
        assert len(self._pips) > 0
        lics = {}
        for pip in self._pips:
            logging.info("   ...examining '%s'", pip)
            self._add_pip_license_for(pip, None, lics)
        return lics.values()

    def _load_pip_prerequisites(self):
        self._pips = []
        for entry in _read_json_file(_PREREQS_FILE):
            if 'pip' in entry:
                self._pips.append(entry['pip'])

    @classmethod
    def _get_pip_module_details(cls, pip: str) -> Dict:
        details = {}
        for line in _process("python3 -m pip show %s" % pip):
            line = line.decode('utf-8').rstrip()
            detail = line.split(':', 1)
            assert len(detail) > 0, 'it should not be possible to get nothing here'
            key = detail[0]
            value = None
            if len(detail) > 1:
                value = detail[1].strip()
                if value == '':
                    value = None
                if key == 'Requires' and value is not None:
                    value = [x.strip() for x in value.split(',')]
            if value is not None:
                details[key] = value
        return details

    @classmethod
    def _get_pip_license_filename(cls, pipdetails: Dict) -> str:
        location = pipdetails.get('Location', None)
        version = pipdetails.get('Version', None)
        pipname = pipdetails.get('Name', None)
        if location and version and pipname:
            dirname = "%s/%s-%s.dist-info" % (location, pipname, version)
            filename = _get_license_filename(dirname)
            if not filename:
                dirname = "%s/%s-%s.dist-info" % (location, pipname.replace('-', '_'), version)
                filename = _get_license_filename(dirname)
            if filename:
                return "%s/%s" % (dirname, filename)
        return None

    def _add_pip_license_for(self, pip: str, used_by: str, licenses: Dict):
        if pip not in licenses:
            lic = {'moduleName': pip}
            details = self._get_pip_module_details(pip)
            if not details:
                lic['moduleLicense'] = 'Unknown'
            else:
                requires = details.get('Requires', [])
                if requires:
                    logging.info("      %s: also found %s", pip, requires)
                    for req in requires:
                        self._add_pip_license_for(req, pip, licenses)
                licensetype = details.get('License', None)
                entry = self.spdx.search(licensetype)
                if not entry:
                    licensefilename = self._get_pip_license_filename(details)
                    if licensefilename:
                        newlicensetype = self.guess_license_with_ninka(licensefilename)
                        entry = self.spdx.search(newlicensetype)
                if entry:
                    licensetype = entry['name']
                lic['moduleLicense'] = licensetype
                lic['moduleVersion'] = details.get('Version', None)
                lic['moduleUrl'] = details.get('Home-page', None)
            if used_by:
                self.ensure_used_by(used_by, lic)
            licenses[pip] = lic


# MARK: Main Entry Point

def _write_licenses(licenses: Dict):
    if len(licenses) > 0:
        if not os.path.isdir('Dependencies'):
            os.mkdir('Dependencies')
        data = {'dependencies': sorted(licenses.values(), key=lambda x: x['moduleName'])}
        with open(_PREREQS_LICENSE_FILE, 'w') as outfile:
            json.dump(data, outfile, indent=4, sort_keys=True)
    else:
        logging.info("No dependencies found.")

def _get_module_name() -> str:
    return os.path.basename(os.getcwd())

def _parse_command_line():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true', help='Show debugging information')
    return parser.parse_args()

def _main():
    args = _parse_command_line()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    modulename = _get_module_name()
    licenses = {}
    scanners = [ManuallyEditedScanner(),
                KSSPrereqScanner(),
                SwiftModuleScanner(),
                PipScanner()]
    for scanner in scanners:
        scanner.add_licenses(modulename, licenses)
    _write_licenses(licenses)

if __name__ == '__main__':
    if not os.path.isdir('BuildSystem'):
        print('Script must be run from the project directory.', file=sys.stderr)
        sys.exit(-1)
    _main()
