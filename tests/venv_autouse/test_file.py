#!/usr/bin/env python3
"""
Tests for "file.py".
"""
from inspect import currentframe
from pathlib import Path
from shutil import rmtree
from subprocess import run
import sys
from os import environ

# pylint: disable=[import-error]
import pytest  # type: ignore
# to test exceptions: with pytest.raises()

# Cheat package to not execute
environ['PYTHON_VENV_AUTOUSE_SUBPROCESS'] = '1'

# pylint: disable=[import-error,wrong-import-position]
from src.venv_autouse import file  # noqa: E402

# Disable cheat
del environ['PYTHON_VENV_AUTOUSE_SUBPROCESS']


# Backup some data
ORIG_IS_WINDOWS = file.IS_WINDOWS
ORIG_FILENAME = file.FILENAME
ORIG_DIR_REQ_FILENAME = file.DIR_REQ_FILENAME
ORIG_FILE_REQ_FILENAME = file.FILE_REQ_FILENAME
ORIG_VENV_DIR = file.VENV_DIR
ORIG_VENV_HASH_FILE = file.VENV_HASH_FILE
ORIG_VENV_HASH = dict(file.VENV_HASH)
ORIG_REQ_FILES = dict(file.REQ_FILES)


def restore() -> None:
    """ Restore original values """
    file.IS_WINDOWS = ORIG_IS_WINDOWS
    file.FILENAME = ORIG_FILENAME
    file.DIR_REQ_FILENAME = ORIG_DIR_REQ_FILENAME
    file.FILE_REQ_FILENAME = ORIG_FILE_REQ_FILENAME
    file.VENV_DIR = ORIG_VENV_DIR
    file.VENV_HASH_FILE = ORIG_VENV_HASH_FILE
    file.VENV_HASH = dict(ORIG_VENV_HASH)
    file.REQ_FILES = dict(ORIG_REQ_FILES)

    rmtree(file.VENV_DIR, ignore_errors=True)


FOO_FILE = Path('foo')
SAMPLE_REQ_FILE = Path(__file__).parent / 'sample_req.txt'
SAMPLE_REQ_FILE_HASH = 'f7e270c8a03ff7dc90ff31aec88380e708deddc4ac91d5dbe7e64363ecdbeed7'
SAMPLE_REQ_FILE2 = Path(__file__).parent / 'sample_req2.txt'
SAMPLE_HASH_FILE = Path(__file__).parent / 'sample_hash_file.txt'


def test_execute_file() -> None:
    """ Test executing the file raises an exception. """
    venv_autouse_file = Path(__file__).resolve().parents[2] / 'src' / 'venv_autouse' / 'file.py'
    process = run([venv_autouse_file], check=False)
    assert process.returncode != 0


def test_get_filename_from_caller() -> None:
    """ get_filename_from_caller """
    assert file.get_filename_from_caller(currentframe()) == __file__


def test_get_caller_filename() -> None:
    """ get_caller_filename """
    assert file.get_caller_filename().name == '__main__.py'
    assert file.get_caller_filename().parts[-2] == 'pytest'


def test_digest_file_nonexistent() -> None:
    """ digest_file with non-existent file """
    assert file.digest_file(FOO_FILE) == ''


def test_digest_file_existing() -> None:
    """ digest_file with existing file"""
    assert file.digest_file(SAMPLE_REQ_FILE) == SAMPLE_REQ_FILE_HASH


def test_venv_get_exe_linux() -> None:
    """ venv_get_exe on linux """
    file.IS_WINDOWS = False
    assert str(file.venv_get_exe()) == str(file.VENV_DIR / 'bin' / 'python')

    restore()


def test_venv_get_exe_windows() -> None:
    """ venv_get_exe on windows """
    file.IS_WINDOWS = True
    assert str(file.venv_get_exe()) == str(file.VENV_DIR / 'Scripts' / 'python.exe')

    restore()


def test_venv_hash_readlines_nofile() -> None:
    """ venv_hash_readlines with no file """
    assert file.venv_hash_readlines() == []


def test_venv_hash_readlines_file() -> None:
    """ venv_hash_readlines with a file """
    file.VENV_HASH_FILE = SAMPLE_HASH_FILE
    assert file.venv_hash_readlines() == ['foo:bar', 'hello:world']

    restore()


def test_venv_hash_parse_nofile() -> None:
    """ venv_hash_parse with no file """
    assert file.venv_hash_parse() == {}


def test_venv_hash_parse_file() -> None:
    """ venv_hash_parse with a file """
    file.VENV_HASH_FILE = SAMPLE_HASH_FILE
    assert file.venv_hash_parse() == {'foo': 'bar', 'hello': 'world'}

    restore()


def test_venv_create_skipped() -> None:
    """ venv_create but skipped """
    file.VENV_DIR.mkdir()
    file.venv_create()  # nothing happens

    restore()


def expect_run_pip_install(fake_process, cmd_args: list) -> None:
    """ Expect a subprocess call to run a pip install command. """
    fake_process.register_subprocess(
        [str(file.venv_get_exe()), '-m', 'pip', 'install'] + cmd_args,
    )


def expect_run_pip_install_self(fake_process) -> None:
    """ Expect a subprocess call to run pip install for this package. """
    expect_run_pip_install(fake_process, [file.PACKAGE_NAME])


def expect_run_ensurepip(fake_process) -> None:
    """ Expect a subprcess call to init venv with pip. """
    m_flag = '-m'

    if sys.version_info.minor < 10:
        m_flag = '-Im'

    fake_process.register_subprocess(
        [str(file.venv_get_exe()), m_flag, 'ensurepip', '--upgrade', '--default-pip'],
    )


def expect_venv_create(fake_process) -> None:
    """ Expect everything we do when calling venv_create. """
    expect_run_ensurepip(fake_process)
    expect_run_pip_install_self(fake_process)


def test_venv_create_do(fake_process) -> None:
    """ venv_create for real """
    expect_venv_create(fake_process)

    file.venv_create()
    assert file.VENV_DIR.exists()

    restore()


def test_venv_hash_check_nofile() -> None:
    """ venv_hash_check with no file """
    assert not file.venv_hash_check(FOO_FILE)


def test_venv_hash_check_wrong_hash() -> None:
    """ venv_hash_check with a file having the wrong hash """
    file.VENV_HASH = {SAMPLE_REQ_FILE.name: SAMPLE_REQ_FILE_HASH + 'foo'}
    assert not file.venv_hash_check(SAMPLE_REQ_FILE)

    restore()


def test_venv_hash_check_match() -> None:
    """ venv_hash_check with the file matching the hash """
    file.VENV_HASH = {SAMPLE_REQ_FILE.name: SAMPLE_REQ_FILE_HASH}
    assert file.venv_hash_check(SAMPLE_REQ_FILE)

    restore()


def expect_run_pip_install_file(fake_process, filename: Path) -> None:
    """ Expect a subprocess call to run a pip install with file command. """
    expect_run_pip_install(fake_process, ['-r', str(filename)])


def test_run_pip_install_file(fake_process) -> None:
    """ run_pip_install_file """
    expect_run_pip_install_file(fake_process, FOO_FILE)
    file.run_pip_install_file(FOO_FILE)


def test_venv_apply_req_file_nofile(fake_process) -> None:
    """ venv_apply_req_file with no req file """
    expect_run_pip_install_file(fake_process, FOO_FILE)
    file.venv_apply_req_file(FOO_FILE)
    assert FOO_FILE.name not in file.VENV_HASH

    restore()


def test_venv_apply_req_file_exist_not_digested(fake_process) -> None:
    """ venv_apply_req_file with a real req file not digested """
    expect_run_pip_install_file(fake_process, SAMPLE_REQ_FILE)
    file.venv_apply_req_file(SAMPLE_REQ_FILE)
    assert SAMPLE_REQ_FILE.name in file.VENV_HASH
    assert file.VENV_HASH[SAMPLE_REQ_FILE.name] == SAMPLE_REQ_FILE_HASH

    restore()


def test_venv_apply_req_file_exist_digested(fake_process) -> None:
    """ venv_apply_req_file with a real req file already digested """
    file.REQ_FILES[SAMPLE_REQ_FILE] = SAMPLE_REQ_FILE_HASH
    expect_run_pip_install_file(fake_process, SAMPLE_REQ_FILE)

    file.venv_apply_req_file(SAMPLE_REQ_FILE)

    assert SAMPLE_REQ_FILE.name in file.VENV_HASH
    assert file.VENV_HASH[SAMPLE_REQ_FILE.name] == SAMPLE_REQ_FILE_HASH

    restore()


def test_venv_apply_req_file_exist_digested_and_match(fake_process) -> None:
    """ venv_apply_req_file with a real req file already digested and matching """
    file.REQ_FILES[SAMPLE_REQ_FILE] = SAMPLE_REQ_FILE_HASH
    file.VENV_HASH[SAMPLE_REQ_FILE.name] = SAMPLE_REQ_FILE_HASH
    expect_run_pip_install_file(fake_process, SAMPLE_REQ_FILE)

    file.venv_apply_req_file(SAMPLE_REQ_FILE)

    assert SAMPLE_REQ_FILE.name in file.VENV_HASH
    assert file.VENV_HASH[SAMPLE_REQ_FILE.name] == SAMPLE_REQ_FILE_HASH

    restore()


def test_venv_update_nofile() -> None:
    """ venv_update with no req file available """
    file.VENV_DIR.mkdir()
    assert not file.venv_update()

    restore()


def test_venv_update_one_file(fake_process) -> None:
    """ venv_update with one req file available """
    file.VENV_HASH_FILE = Path(__file__).parent / 'tmp_venv_hash_file_one_file.txt'
    file.DIR_REQ_FILENAME = SAMPLE_REQ_FILE

    expect_venv_create(fake_process)
    expect_run_pip_install_file(fake_process, SAMPLE_REQ_FILE)
    file.venv_update()

    assert file.venv_hash_parse() == {SAMPLE_REQ_FILE.name: SAMPLE_REQ_FILE_HASH}

    restore()


def test_venv_update_two_files(fake_process) -> None:
    """ venv_update with two req files available """
    file.VENV_HASH_FILE = Path(__file__).parent / 'tmp_venv_hash_file_two_files.txt'
    file.DIR_REQ_FILENAME = SAMPLE_REQ_FILE
    file.FILE_REQ_FILENAME = SAMPLE_REQ_FILE2

    expect_venv_create(fake_process)
    expect_run_pip_install_file(fake_process, SAMPLE_REQ_FILE)
    expect_run_pip_install_file(fake_process, SAMPLE_REQ_FILE2)
    file.venv_update()

    assert file.venv_hash_parse() == {
        SAMPLE_REQ_FILE.name: SAMPLE_REQ_FILE_HASH,
        SAMPLE_REQ_FILE2.name: '7268a6b8e8450e70926eab67446285299a91b3672b5cc58847cd0ac0b9b415ef',
    }

    restore()


def test_main_env_var() -> None:
    """ main skipped due to env var """
    environ['PYTHON_VENV_AUTOUSE_SUBPROCESS'] = '1'
    file.main()  # nothing happens

    del environ['PYTHON_VENV_AUTOUSE_SUBPROCESS']


def test_main_no_req_file() -> None:
    """ main with no req file """
    assert all(sha == '' for sha in list(file.REQ_FILES.values()))
    file.main()  # nothing happens


def test_main_return() -> None:
    """ main with venv not updated """
    file.REQ_FILES = {key: 'foo' for key in file.REQ_FILES}
    file.VENV_DIR.mkdir()

    # Cheat so we beleive we are in venv
    file.VENV_DIR = Path(sys.prefix)

    file.main()  # nothing happens

    restore()


def test_main_subprocess(fake_process) -> None:
    """ main with venv update """
    file.REQ_FILES = {key: 'foo' for key in file.REQ_FILES}
    file.VENV_DIR.mkdir()

    fake_process.register_subprocess([str(file.venv_get_exe())] + sys.argv)

    with pytest.raises(SystemExit) as sys_exit:
        file.main()

    # assert environ[file.ENV_VAR_PREVENT_RECURSION] == '1'  # only in subprocess, how to assert???
    assert sys_exit.value.code is None

    restore()
