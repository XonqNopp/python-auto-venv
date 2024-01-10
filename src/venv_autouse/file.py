#!/usr/bin/env python3
"""
Auto-venv on a per-file basis.

This will use a venv only specific to the file it is imported into.
"""
import sys
from os import environ
import venv
from pathlib import Path
from inspect import currentframe
import hashlib
from subprocess import run
from platform import system


if __name__ == '__main__':
    raise RuntimeError('This package cannot be executed, it can only be imported.')


PACKAGE_NAME = 'venv_autouse'
ENV_VAR_PREVENT_RECURSION = f'PYTHON_{PACKAGE_NAME.upper()}_SUBPROCESS'
IS_WINDOWS = system().lower() == 'windows'


def get_filename_from_caller(caller) -> str:
    """
    Get the filename from the provided caller.
    """
    return caller.f_code.co_filename


def get_caller_filename() -> Path:
    """
    Get the caller.
    """
    parents = []

    parent_caller = currentframe()
    while parent_caller is not None:
        parent_filename = get_filename_from_caller(parent_caller)

        parent_caller = parent_caller.f_back

        if parent_filename == __file__:
            # ignore if we match this file
            continue

        if parent_filename.startswith('<'):
            # ignore if we find a python internal frame
            continue

        if Path(parent_filename).name == 'runpy.py':
            # ignore if command was "python -m"
            continue

        parents.append(parent_filename)

    if len(parents) == 0:
        raise RuntimeError(f'Unable to determine parent caller for {currentframe()}')

    filename = Path(parents[-1])

    if not filename.exists():
        raise RuntimeError(f'Unable to determine parent caller: {parents}')

    return filename


def digest_file(file: Path) -> str:
    """
    Digest a file.
    """
    if not file.exists():
        return ''

    return hashlib.sha3_256(file.read_bytes()).hexdigest()


FILENAME = get_caller_filename()
DIR_REQ_FILENAME = FILENAME.parent / 'requirements.txt'
FILE_REQ_FILENAME = FILENAME.with_suffix('.req.txt')

REQ_FILES: dict[Path, str] = {
    filename: digest_file(filename)
    for filename in [DIR_REQ_FILENAME, FILE_REQ_FILENAME]
}

VENV_DIR = FILENAME.parent / f'.{FILENAME.with_suffix("").name}.venv'
VENV_HASH_FILE = VENV_DIR / 'hash.req.txt'


def venv_get_exe() -> Path:
    """
    Get the venv executable (depends on the platform).
    """
    bin_dir = 'bin'
    exe = 'python'

    if IS_WINDOWS:
        bin_dir = 'Scripts'
        exe = 'python.exe'

    return VENV_DIR / bin_dir / exe


def venv_hash_readlines() -> list[str]:
    """
    Read the custom hash file we use in the venv dir.
    """
    if not VENV_HASH_FILE.exists():
        return []

    return VENV_HASH_FILE.read_text().splitlines()


def venv_hash_parse() -> dict:
    """
    Parse the custom hash file we use in the venv dir.
    """
    contents = venv_hash_readlines()
    if contents == []:
        return {}

    checks: dict[str, str] = {}
    for line in contents:
        key, value = line.strip().split(':', 1)
        checks[key] = value

    return checks


VENV_HASH = venv_hash_parse()
VENV_HASH_ORIG = dict(VENV_HASH)  # copy so we can check if it changed


def run_pip_install(cmd_args: list) -> None:
    """
    Run a pip command (subprocess) to install.
    """
    run([str(venv_get_exe()), '-m', 'pip', 'install'] + cmd_args, check=True)


def venv_create() -> None:
    """
    Create the venv if it does not exist already.
    """
    if VENV_DIR.exists():
        return

    venv.create(VENV_DIR, with_pip=True)

    # We need also this package installed or execution will fail
    run_pip_install([PACKAGE_NAME])


def venv_hash_check(req_file: Path) -> bool:
    """
    Check if the hash of the requirements file match.
    """
    if req_file.name not in VENV_HASH:
        return False

    if req_file not in REQ_FILES:
        # Should not happen but better be safe
        REQ_FILES[req_file] = digest_file(req_file)

    return VENV_HASH[req_file.name] == REQ_FILES[req_file]


def run_pip_install_file(filename: Path) -> None:
    """
    Run a pip command (subprocess) to install from a requirements file.
    """
    run_pip_install(['-r', str(filename)])


def venv_apply_req_file(req_file: Path) -> bool:
    """
    Install requirements file with pip.
    """
    if not req_file.exists():
        return False

    if venv_hash_check(req_file):
        return False

    run_pip_install_file(req_file)

    # update hash
    if req_file in REQ_FILES:
        # Already computed
        VENV_HASH[req_file.name] = REQ_FILES[req_file]
    else:
        VENV_HASH[req_file.name] = digest_file(req_file)

    return True


def venv_update() -> bool:
    """
    Update the venv if needed.

    Returns:
        bool: True if updated, False if not changed
    """
    venv_create()

    dir_req_file_updated = venv_apply_req_file(DIR_REQ_FILENAME)
    file_req_file_updated = venv_apply_req_file(FILE_REQ_FILENAME)

    if not dir_req_file_updated and not file_req_file_updated:
        return False

    # write hash file
    hashes = [f'{key}:{value}' for key, value in VENV_HASH.items() if value is not None]
    VENV_HASH_FILE.write_text('\n'.join(hashes))

    return True


def main() -> None:
    """
    Main function executed when this package is imported.
    """
    if ENV_VAR_PREVENT_RECURSION in environ:
        # Already running from here, no need to do any check
        return

    if all(sha == '' for sha in REQ_FILES.values()):
        # No requirements file found, abort
        return

    subprocess_needed = venv_update()

    if not subprocess_needed:
        # check if in venv
        subprocess_needed = VENV_DIR.name != Path(sys.prefix).name

    if not subprocess_needed:
        # Return to caller and let it continue
        return

    # subprocess and exit (do not return to caller)
    env_vars = dict(environ)
    env_vars[ENV_VAR_PREVENT_RECURSION] = '1'
    run([str(venv_get_exe())] + sys.argv, check=True, env=env_vars)
    sys.exit()


main()
