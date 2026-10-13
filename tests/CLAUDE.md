# tests/
> L2 | 父级: ../CLAUDE.md

离线验证提词、信号判定、存储和报告。
网络调用使用替身，不证明上游接口可用。

成员清单
conftest.py: pytest 自动重置报告语言，隔离配置副本，并断开 GoAnyAPI 网络。
test_radar.py: 验证提词、信号阈值、存储、模型解析、复盘、新词表和输出。
test_doctor.py: 验证起飞前检查的阻挡判定、成本模型与不泄密。
fixtures/: 保存上游响应样本；参见 fixtures/CLAUDE.md。

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
