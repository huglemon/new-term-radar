# --- 文件契约 ---
# [INPUT]: 依赖 pathlib、gzip 与 JSON。
# [OUTPUT]: 提供快照 load、save；缺失文件返回 None。
# [POS]: radar 的文件状态边界，供采集信号比较前次结果。
# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""Snapshots: yesterday's state of each signal, gzip JSON files in the state directory."""
from __future__ import annotations

import gzip
import json
from pathlib import Path


def load(path: Path):
    return json.loads(gzip.decompress(path.read_bytes())) if path.exists() else None


def save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(data, ensure_ascii=False).encode()))
