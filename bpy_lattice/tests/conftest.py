import pathlib

import pytest

TESTS_ROOT = pathlib.Path(__file__).resolve().parent
LATTICES_ROOT = TESTS_ROOT / "bmad"
TEST_ARTIFACTS = TESTS_ROOT / "artifacts"


@pytest.fixture(autouse=True, scope="session")
def _test_artifacts_dir():
    TEST_ARTIFACTS.mkdir(exist_ok=True, parents=True)
