#!/usr/bin/env python3
"""
Tests for "common.py".
"""

# pylint: disable=[redefined-outer-name,unused-argument]
# redefined-outer-name: we can define a fixture and use it as arg to functions (pytest feature).
# unused-argument: we need to use fake_process to register unwanted processes

from inspect import currentframe
from pathlib import Path
from shutil import rmtree
from subprocess import run
import sys
from os import environ
from collections.abc import Generator

# pylint: disable=[import-error]
import pytest  # type: ignore

# pylint: disable=[import-error]
from src.venv_autouse import common  # noqa: E402


TEST_DIR = Path(__file__).parent

FOO_FILE = TEST_DIR / Path('foo')
SAMPLE_REQ_FILE = TEST_DIR / 'sample_req.txt'
SAMPLE_REQ_FILE_HASH = 'f7e270c8a03ff7dc90ff31aec88380e708deddc4ac91d5dbe7e64363ecdbeed7'
SAMPLE_REQ_FILE2 = TEST_DIR / 'sample_req2.txt'
SAMPLE_HASH_FILE = TEST_DIR / 'sample_hash_file.txt'


def touch(file: Path) -> None:
    """ Be sure a file exists. """
    file.parent.mkdir(exist_ok=True, parents=True)
    file.touch()


@pytest.fixture
def venvauto() -> Generator[common.VenvAutouse, None, None]:
    """
    Test fixture to get a venv autouse instance and do the cleanup after.
    """

    # pylint: disable=[too-few-public-methods]
    class TestVenvAutouse(common.VenvAutouse):
        """ Just make a copy so we can change class constants. """
        def __init__(self):
            super().__init__()

            venv_dir_prefix = f'.{self.filename.with_suffix("").name}'
            if self.VENV_DIR_PREFIX is not None:
                venv_dir_prefix = self.VENV_DIR_PREFIX

            self.venv_dir = TEST_DIR / f'venv_dummy.{venv_dir_prefix}.venv'
            self.venv_dummy = self.venv_dir  # copy to keep it for tear down

            self.venv_hash_file = self.venv_dir / 'hash.req.txt'
            self.venv_hash = self.venv_hash_parse()

            self.fake_package = self.venv_dir / self.PACKAGE_NAME

    venv_autouse_instance = TestVenvAutouse()

    yield venv_autouse_instance

    # tear down
    venv_autouse_instance.fake_package.unlink(missing_ok=True)
    rmtree(venv_autouse_instance.venv_dummy, ignore_errors=True)


def test_execute_file() -> None:
    """ Test executing the file raises an exception. """
    root_dir = Path(__file__).resolve().parents[2]
    venv_autouse_file = root_dir / 'src' / 'venv_autouse' / 'common.py'
    process = run([venv_autouse_file], check=False)
    assert process.returncode != 0


def test_get_filename_from_caller() -> None:
    """ get_filename_from_caller """
    assert common.VenvAutouse.get_filename_from_caller(currentframe()) == __file__


def test_get_caller_filename(venvauto) -> None:
    """ get_caller_filename """
    caller_filename = venvauto.get_caller_filename()
    assert caller_filename.name == '__main__.py'
    assert caller_filename.parts[-2] == 'pytest'


def test_digest_file_nonexistent() -> None:
    """ digest_file with non-existent file """
    assert common.VenvAutouse.digest_file(FOO_FILE) == ''


def test_digest_file_existing() -> None:
    """ digest_file with existing file"""
    assert common.VenvAutouse.digest_file(SAMPLE_REQ_FILE) == SAMPLE_REQ_FILE_HASH


def test_venv_get_exe_linux(venvauto) -> None:
    """ venv_get_exe on linux """
    venvauto.IS_WINDOWS = False
    assert str(venvauto.venv_get_exe()) == str(venvauto.venv_dir / 'bin' / 'python')


def test_venv_get_exe_windows(venvauto) -> None:
    """ venv_get_exe on windows """
    venvauto.IS_WINDOWS = True
    assert str(venvauto.venv_get_exe()) == str(venvauto.venv_dir / 'Scripts' / 'python.exe')


def test_venv_hash_readlines_nofile(venvauto) -> None:
    """ venv_hash_readlines with no file """
    assert venvauto.venv_hash_readlines() == []


def test_venv_hash_readlines_file(venvauto) -> None:
    """ venv_hash_readlines with a file """
    venvauto.venv_hash_file = SAMPLE_HASH_FILE
    assert venvauto.venv_hash_readlines() == ['foo:bar', 'hello:world']


def test_venv_hash_parse_nofile(venvauto) -> None:
    """ venv_hash_parse with no file """
    assert venvauto.venv_hash_parse() == {}


def test_venv_hash_parse_file(venvauto) -> None:
    """ venv_hash_parse with a file """
    venvauto.venv_hash_file = SAMPLE_HASH_FILE
    assert venvauto.venv_hash_parse() == {'foo': 'bar', 'hello': 'world'}


def test_venv_create_skipped(venvauto) -> None:
    """ venv_create but skipped """
    venvauto.venv_dir.mkdir()
    venvauto.venv_create()


def expect_run_pip_install(venvauto, fake_process, cmd_args: list) -> None:
    """ Expect a subprocess call to run a pip install command. """
    fake_process.register_subprocess(
        [str(venvauto.venv_get_exe()), '-m', 'pip', 'install'] + cmd_args,
    )


def expect_run_pip_download_self(venvauto, fake_process) -> None:
    """ Expect a subprocess call to run pip download for this package, and touch fake file. """
    fake_process.register_subprocess(
        [str(venvauto.venv_get_exe()), '-m', 'pip', 'download', venvauto.PACKAGE_NAME],
    )

    touch(venvauto.fake_package)


def expect_run_pip_install_self(venvauto, fake_process) -> None:
    """ Expect a subprocess call to run pip install for this package. """
    expect_run_pip_install(venvauto, fake_process, [str(venvauto.fake_package)])


def expect_run_ensurepip(venvauto, fake_process) -> None:
    """ Expect a subprcess call to init venv with pip. """
    m_flag = '-m'

    if sys.version_info.minor < 10:
        m_flag = '-Im'

    fake_process.register_subprocess(
        [str(venvauto.venv_get_exe()), m_flag, 'ensurepip', '--upgrade', '--default-pip'],
    )


def expect_venv_create(venvauto, fake_process) -> None:
    """ Expect everything we do when calling venv_create. """
    expect_run_ensurepip(venvauto, fake_process)


def test_venv_create_do(venvauto, fake_process) -> None:
    """ venv_create for real """
    expect_venv_create(venvauto, fake_process)

    venvauto.venv_create()
    assert venvauto.venv_dir.exists()


def test_venv_hash_check_nofile(venvauto) -> None:
    """ venv_hash_check with no file """
    assert not venvauto.venv_hash_check(FOO_FILE)


def test_venv_hash_check_wrong_hash(venvauto) -> None:
    """ venv_hash_check with a file having the wrong hash """
    venvauto.venv_hash = {SAMPLE_REQ_FILE.name: SAMPLE_REQ_FILE_HASH + 'foo'}
    assert not venvauto.venv_hash_check(SAMPLE_REQ_FILE)


def test_venv_hash_check_match(venvauto) -> None:
    """ venv_hash_check with the file matching the hash """
    venvauto.venv_hash = {SAMPLE_REQ_FILE.name: SAMPLE_REQ_FILE_HASH}
    assert venvauto.venv_hash_check(SAMPLE_REQ_FILE)


def test_venv_install_self_file_downloaded(venvauto, fake_process) -> None:
    """ venv_install_self but wheel file is already downloaded """
    touch(venvauto.fake_package)
    expect_run_pip_install_self(venvauto, fake_process)

    venvauto.venv_install_self()


def test_venv_install_self_file_installed(venvauto, fake_process) -> None:
    """ venv_install_self but wheel file is already installed """
    wheel = venvauto.venv_dir / (venvauto.PACKAGE_NAME + '-py3-none-any.whl')

    dist_info = (
        venvauto.venv_dir
        / 'lib'
        / 'python3'
        / 'site-packages'
        / (venvauto.PACKAGE_NAME + '.dist-info')
    )

    touch(wheel)
    touch(dist_info)

    venvauto.venv_install_self()


def test_venv_install_self_nofile(venvauto, fake_process) -> None:
    """ venv_install_self but needs to download and install file """
    expect_run_pip_download_self(venvauto, fake_process)
    expect_run_pip_install_self(venvauto, fake_process)

    venvauto.venv_install_self()


def expect_run_pip_install_file(venvauto, fake_process, filename: Path) -> None:
    """ Expect a subprocess call to run a pip install with file command. """
    expect_run_pip_install(venvauto, fake_process, ['-r', str(filename)])


def test_run_pip_install_file(venvauto, fake_process) -> None:
    """ run_pip_install_file """
    expect_run_pip_install_file(venvauto, fake_process, FOO_FILE)
    venvauto.run_pip_install_file(FOO_FILE)


def test_venv_apply_req_file_nofile(venvauto, fake_process) -> None:
    """ venv_apply_req_file with no req file """
    expect_run_pip_install_file(venvauto, fake_process, FOO_FILE)
    venvauto.venv_apply_req_file(FOO_FILE)
    assert FOO_FILE.name not in venvauto.venv_hash


def test_venv_apply_req_file_exist_not_digested(venvauto, fake_process) -> None:
    """ venv_apply_req_file with a real req file not digested """
    expect_run_pip_install_file(venvauto, fake_process, SAMPLE_REQ_FILE)
    venvauto.venv_apply_req_file(SAMPLE_REQ_FILE)
    assert SAMPLE_REQ_FILE.name in venvauto.venv_hash
    assert venvauto.venv_hash[SAMPLE_REQ_FILE.name] == SAMPLE_REQ_FILE_HASH


def test_venv_apply_req_file_exist_digested(venvauto, fake_process) -> None:
    """ venv_apply_req_file with a real req file already digested """
    venvauto.req_files[SAMPLE_REQ_FILE] = SAMPLE_REQ_FILE_HASH
    expect_run_pip_install_file(venvauto, fake_process, SAMPLE_REQ_FILE)

    venvauto.venv_apply_req_file(SAMPLE_REQ_FILE)

    assert SAMPLE_REQ_FILE.name in venvauto.venv_hash
    assert venvauto.venv_hash[SAMPLE_REQ_FILE.name] == SAMPLE_REQ_FILE_HASH


def test_venv_apply_req_file_exist_digested_and_match(venvauto, fake_process) -> None:
    """ venv_apply_req_file with a real req file already digested and matching """
    venvauto.req_files[SAMPLE_REQ_FILE] = SAMPLE_REQ_FILE_HASH
    venvauto.venv_hash[SAMPLE_REQ_FILE.name] = SAMPLE_REQ_FILE_HASH
    expect_run_pip_install_file(venvauto, fake_process, SAMPLE_REQ_FILE)

    venvauto.venv_apply_req_file(SAMPLE_REQ_FILE)

    assert SAMPLE_REQ_FILE.name in venvauto.venv_hash
    assert venvauto.venv_hash[SAMPLE_REQ_FILE.name] == SAMPLE_REQ_FILE_HASH


def test_venv_update_nofile(venvauto, fake_process) -> None:
    """ venv_update with no req file available """
    venvauto.venv_dir.mkdir()
    touch(venvauto.fake_package)
    expect_run_pip_install_self(venvauto, fake_process)
    assert not venvauto.venv_update()


def test_venv_update_one_file(venvauto, fake_process) -> None:
    """ venv_update with one req file available """
    venvauto.venv_hash_file = Path(__file__).parent / 'tmp_venv_hash_file_one_file.txt'
    venvauto.dir_req_filename = SAMPLE_REQ_FILE

    expect_venv_create(venvauto, fake_process)
    touch(venvauto.fake_package)
    expect_run_pip_install_self(venvauto, fake_process)
    expect_run_pip_install_file(venvauto, fake_process, SAMPLE_REQ_FILE)
    venvauto.venv_update()

    assert venvauto.venv_hash_parse() == {SAMPLE_REQ_FILE.name: SAMPLE_REQ_FILE_HASH}


def test_venv_update_two_files(venvauto, fake_process) -> None:
    """ venv_update with two req files available """
    venvauto.venv_hash_file = Path(__file__).parent / 'tmp_venv_hash_file_two_files.txt'
    venvauto.dir_req_filename = SAMPLE_REQ_FILE
    venvauto.file_req_filename = SAMPLE_REQ_FILE2

    expect_venv_create(venvauto, fake_process)
    touch(venvauto.fake_package)
    expect_run_pip_install_self(venvauto, fake_process)
    expect_run_pip_install_file(venvauto, fake_process, SAMPLE_REQ_FILE)
    expect_run_pip_install_file(venvauto, fake_process, SAMPLE_REQ_FILE2)
    venvauto.venv_update()

    assert venvauto.venv_hash_parse() == {
        SAMPLE_REQ_FILE.name: SAMPLE_REQ_FILE_HASH,
        SAMPLE_REQ_FILE2.name: '7268a6b8e8450e70926eab67446285299a91b3672b5cc58847cd0ac0b9b415ef',
    }


def test_execute_env_var(venvauto, fake_process) -> None:
    """ execute skipped due to env var """
    environ['PYTHON_VENV_AUTOUSE_SUBPROCESS'] = '1'
    venvauto.execute()

    del environ['PYTHON_VENV_AUTOUSE_SUBPROCESS']


def test_execute_no_req_file(venvauto, fake_process) -> None:
    """ execute with no req file """
    assert all(sha == '' for sha in list(venvauto.req_files.values()))
    venvauto.execute()


def test_execute_return(venvauto, fake_process) -> None:
    """ execute with venv not updated """
    # Cheat so we beleive we are in venv
    venvauto.venv_dir = Path(sys.prefix)
    fake_package = venvauto.venv_dir / venvauto.PACKAGE_NAME

    venvauto.req_files = {key: 'foo' for key in venvauto.req_files}

    expect_run_pip_download_self(venvauto, fake_process)
    touch(fake_package)
    expect_run_pip_install(venvauto, fake_process, [str(fake_package)])

    venvauto.execute()

    venvauto.venv_dir = None  # prevent fixture to do teardown


def test_execute_subprocess(venvauto, fake_process) -> None:
    """ execute with venv update """
    venvauto.req_files = {key: 'foo' for key in venvauto.req_files}
    venvauto.venv_dir.mkdir()
    touch(venvauto.fake_package)
    expect_run_pip_install(venvauto, fake_process, [str(venvauto.fake_package)])

    fake_process.register_subprocess([str(venvauto.venv_get_exe())] + sys.argv)

    with pytest.raises(SystemExit) as sys_exit:
        venvauto.execute()

    # assert environ[common.ENV_VAR_PREVENT_RECURSION]=='1' only in subprocess, how assert?
    assert sys_exit.value.code == 0
