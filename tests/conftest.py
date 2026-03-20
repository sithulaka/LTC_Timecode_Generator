"""
Pytest conftest: auto-build libltc if not present, provide libltc_path fixture.
"""
import os
import shutil
import subprocess

import pytest

LIBLTC_PATH = "/tmp/libltc/libltc.so"
LIBLTC_REPO = "https://github.com/x42/libltc.git"
LIBLTC_DIR = "/tmp/libltc"


def _build_libltc():
    """Clone and build libltc from source. Returns True on success."""
    git = shutil.which("git")
    gcc = shutil.which("gcc")
    if not git or not gcc:
        return False

    try:
        if not os.path.isdir(LIBLTC_DIR):
            subprocess.check_call(
                [git, "clone", LIBLTC_REPO, LIBLTC_DIR],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
            )

        src_dir = os.path.join(LIBLTC_DIR, "src")
        subprocess.check_call(
            [
                gcc, "-shared", "-fPIC",
                "-o", LIBLTC_PATH,
                "-I", src_dir,
                os.path.join(src_dir, "ltc.c"),
                os.path.join(src_dir, "decoder.c"),
                os.path.join(src_dir, "encoder.c"),
                os.path.join(src_dir, "timecode.c"),
                "-lm",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
        return os.path.exists(LIBLTC_PATH)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False


@pytest.fixture(scope="session")
def libltc_path():
    """Provide the path to the built libltc shared library.

    If the library does not exist, attempt to clone and build it.
    If git or gcc are unavailable, skip the test.
    """
    if os.path.exists(LIBLTC_PATH):
        return LIBLTC_PATH

    if not _build_libltc():
        pytest.skip(
            "libltc could not be built — git and gcc are required. "
            "Install them or manually build libltc at /tmp/libltc/libltc.so"
        )

    return LIBLTC_PATH
