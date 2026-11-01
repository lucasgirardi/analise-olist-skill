import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / ".claude" / "skills" / "analise-olist" / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def olist_dir() -> Path:
    return RAIZ / "tests" / "fixtures" / "olist_recorte"


@pytest.fixture
def garden_dir() -> Path:
    return RAIZ / "dados" / "garden_shop"


@pytest.fixture
def script() -> Path:
    return SCRIPTS / "analise.py"
