# .github/workflows/
> L2 | 父级: ../CLAUDE.md

成员清单
radar.yml: 每八小时运行 sources，每日运行 daily；串行共享 Actions 缓存中的状态，并上传报告和数据库。
test.yml: 在 Python 3.10 与 3.12 上运行离线 pytest。

RADAR_ENABLED=true 才启动采集任务。
密钥来自 Actions secrets。
缓存丢失会重建快照，并丢失复盘历史。
产物保留三十天，不替代持久存储。

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
