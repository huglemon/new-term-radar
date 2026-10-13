# --- 文件契约 ---
# [INPUT]: 无外部依赖。
# [OUTPUT]: 提供 __version__ 与 HTTP User-Agent 常量 UA。
# [POS]: radar 包标识，供采集模块统一声明请求来源。
# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""new-term-radar: spot the names of new AI products, models and tools before they trend."""
__version__ = "0.1.0"
UA = "new-term-radar/0.1 (+https://github.com/zhuyansen/new-term-radar)"
