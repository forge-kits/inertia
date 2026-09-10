import pytest
from forge_inertia.config import _config, _DEFAULTS
from forge_inertia.share import _reset_shared
from forge_inertia import response as _resp_module


@pytest.fixture(autouse=True)
def reset_inertia_state():
    yield
    _config.clear()
    _config.update(_DEFAULTS)
    _reset_shared()
    _resp_module._root_html = None
