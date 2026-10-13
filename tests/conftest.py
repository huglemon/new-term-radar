# --- 文件契约 ---
# [INPUT]: 依赖 pytest 与 radar.config、radar.goanyapi、radar.i18n。
# [OUTPUT]: 提供语言重置、配置隔离和 GoAnyAPI 断网的测试夹具。
# [POS]: tests 的共享测试环境，防止全局语言污染后续测试。
# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
import copy

import pytest

from radar import config, goanyapi, i18n


@pytest.fixture(autouse=True)
def english(monkeypatch):
    i18n.set_lang("en")
    monkeypatch.delenv("GOANYAPI_API_KEY", raising=False)   # the optional source is off unless a test turns it on

    def no_network(*a, **k):
        raise goanyapi.GoAnyError("no network in tests")
    monkeypatch.setattr(goanyapi, "call", no_network)


@pytest.fixture
def cfg(tmp_path):
    c = copy.deepcopy(config.DEFAULTS)
    c["_dir"] = tmp_path
    return c
