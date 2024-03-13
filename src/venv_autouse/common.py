#!/usr/bin/env python3
"""
Venv autouse common code.
"""
import sys
from os import environ
import venv
from pathlib import Path
from inspect import currentframe
import hashlib
from subprocess import run
from platform import system


class VenvAutouseRuntimeError(RuntimeError):
    """ Runtime error in the context of this package. """


def raise_if_main() -> None:
    """
    Raise an exception if the file is executed as main.
    """
    raise VenvAutouseRuntimeError('This package cannot be executed, it can only be imported.')


if __name__ == '__main__':
    raise_if_main()


class VenvAutouse:
    """
    Venv autouse executer.
    """
    PACKAGE_NAME = 'venv_autouse'
    ENV_VAR_PREVENT_RECURSION = f'PYTHON_{PACKAGE_NAME.upper()}_SUBPROCESS'

    IS_WINDOWS = system().lower() == 'windows'

    VENV_DIR_PREFIX: str | None = None

    def __init__(self):
        self.filename = self.get_caller_filename()

        self.dir_req_filename = self.filename.parent / 'requirements.txt'
        self.file_req_filename = self.filename.with_suffix('.req.txt')

        self.req_files: dict[Path, str] = {
            filename: self.digest_file(filename)
            for filename in [self.dir_req_filename, self.file_req_filename]
        }

        venv_dir_prefix = f'.{self.filename.with_suffix("").name}'
        if self.VENV_DIR_PREFIX is not None:
            venv_dir_prefix = self.VENV_DIR_PREFIX

        self.venv_dir = self.filename.parent / f'{venv_dir_prefix}.venv'

        self.venv_hash_file = self.venv_dir / 'hash.req.txt'
        self.venv_hash = self.venv_hash_parse()

    @staticmethod
    def get_filename_from_caller(caller) -> str:
        """
        Get the filename from the provided caller.
        """
        return caller.f_code.co_filename

    def get_caller_filename(self) -> Path:
        """
        Get the caller.
        """
        parents = []

        parent_caller = currentframe()
        while parent_caller is not None:
            parent_filename = self.get_filename_from_caller(parent_caller)

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
            raise VenvAutouseRuntimeError(f'Unable to determine parent caller for {currentframe()}')

        filename = Path(parents[-1])

        if not filename.exists():
            raise VenvAutouseRuntimeError(f'Unable to determine parent caller: {parents}')

        return filename

    @staticmethod
    def digest_file(file: Path) -> str:
        """
        Digest a file.
        """
        if not file.exists():
            return ''

        return hashlib.sha3_256(file.read_bytes()).hexdigest()

    def venv_get_exe(self) -> Path:
        """
        Get the venv executable (depends on the platform).
        """
        bin_dir = 'bin'
        exe = 'python'

        if self.IS_WINDOWS:
            bin_dir = 'Scripts'
            exe = 'python.exe'

        return self.venv_dir / bin_dir / exe

    def venv_hash_readlines(self) -> list[str]:
        """
        Read the custom hash file we use in the venv dir.
        """
        if not self.venv_hash_file.exists():
            return []

        return self.venv_hash_file.read_text().splitlines()

    def venv_hash_parse(self) -> dict:
        """
        Parse the custom hash file we use in the venv dir.
        """
        contents = self.venv_hash_readlines()
        if contents == []:
            return {}

        checks: dict[str, str] = {}
        for line in contents:
            key, value = line.strip().split(':', 1)
            checks[key] = value

        return checks

    def run_pip_install(self, cmd_args: list) -> None:
        """
        Run a pip command (subprocess) to install.
        """
        run([str(self.venv_get_exe()), '-m', 'pip', 'install'] + cmd_args, check=True)

    def venv_create(self) -> None:
        """
        Create the venv if it does not exist already.
        """
        if self.venv_dir.exists():
            return

        venv.create(self.venv_dir, with_pip=True)

    def venv_hash_check(self, req_file: Path) -> bool:
        """
        Check if the hash of the requirements file match.
        """
        if req_file.name not in self.venv_hash:
            return False

        if req_file not in self.req_files:
            # Should not happen but better be safe
            self.req_files[req_file] = self.digest_file(req_file)

        return self.venv_hash[req_file.name] == self.req_files[req_file]

    def run_pip_install_file(self, filename: Path) -> None:
        """
        Run a pip command (subprocess) to install from a requirements file.
        """
        self.run_pip_install(['-r', str(filename)])

    def venv_install_self(self) -> None:
        """
        Install this package in the venv.

        We need this package in the venv too otherwise the import will fail.
        """
        package = list(self.venv_dir.glob(f'{self.PACKAGE_NAME}*'))

        if len(package) > 0:
            # Already downloaded
            # If more than one package, the latest one should be the last in alphabetical list.
            venv_lib_py = list((self.venv_dir / 'lib').glob('python*'))
            if len(venv_lib_py) == 0:
                # Should not happen but be safe
                self.run_pip_install([str(package[-1])])
                return

            dist_info = (
                venv_lib_py[0]
                / 'site-packages'
                / package[-1].name.replace('-py3-none-any.whl', '.dist-info')
            )

            if dist_info.exists():
                # Already installed
                return

            # install
            self.run_pip_install([str(package[-1])])
            return

        download = run(
            [str(self.venv_get_exe()), '-m', 'pip', 'download', self.PACKAGE_NAME],
            cwd=str(self.venv_dir),
            check=False,
            timeout=3,
        )

        package = list(self.venv_dir.glob(f'{self.PACKAGE_NAME}*'))
        print(f'{package=} {self.venv_dir=}')
        if download.returncode != 0 or len(package) == 0:
            # Something bad happened
            raise VenvAutouseRuntimeError(f'Failed to install self ({download.returncode})')

        # If we match more than one package, the latest one should be the last in alphabetical list.
        self.run_pip_install([str(package[-1])])

    def venv_apply_req_file(self, req_file: Path) -> bool:
        """
        Install requirements file with pip.
        """
        if not req_file.exists():
            return False

        if self.venv_hash_check(req_file):
            return False

        self.run_pip_install_file(req_file)

        # update hash
        if req_file in self.req_files:
            # Already computed
            self.venv_hash[req_file.name] = self.req_files[req_file]
        else:
            self.venv_hash[req_file.name] = self.digest_file(req_file)

        return True

    def venv_update(self) -> bool:
        """
        Update the venv if needed.

        Returns:
            bool: True if updated, False if not changed
        """
        self.venv_create()

        self.venv_install_self()

        dir_req_file_updated = self.venv_apply_req_file(self.dir_req_filename)
        file_req_file_updated = self.venv_apply_req_file(self.file_req_filename)

        if not dir_req_file_updated and not file_req_file_updated:
            return False

        # write hash file
        hashes = [f'{key}:{value}' for key, value in self.venv_hash.items() if value is not None]
        self.venv_hash_file.write_text('\n'.join(hashes))

        return True

    def execute(self) -> None:
        """
        Main function executed when this package is imported.
        """
        if self.ENV_VAR_PREVENT_RECURSION in environ:
            # Already running from here, no need to do any check
            return

        if all(sha == '' for sha in self.req_files.values()):
            # No requirements file found, abort
            return

        subprocess_needed = self.venv_update()

        if not subprocess_needed:
            # check if in venv
            subprocess_needed = self.venv_dir.resolve() != Path(sys.prefix).resolve()

        if not subprocess_needed:
            # Return to caller and let it continue
            return

        # subprocess and exit (do not return to caller)
        env_vars = dict(environ)
        env_vars[self.ENV_VAR_PREVENT_RECURSION] = '1'
        process = run([str(self.venv_get_exe())] + sys.argv, check=False, env=env_vars)
        sys.exit(process.returncode)
