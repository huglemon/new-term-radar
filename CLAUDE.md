# new-term-radar - 提前发现 AI 新名称的命令行雷达
Python 3.10+ 标准库 + SQLite + gzip JSON + GitHub Actions

<directory>
radar/ - 采集、提词、筛选、复盘与报告的运行包。
scripts/ - Google Search Console 本机授权工具。
tests/ - 离线逻辑回归测试（1 子目录: fixtures）。
docs/ - 流程图的生成器与产物。
.github/ - CI 配置（1 子目录: workflows）。
</directory>

<config>
config.example.json - 公开配置示例，定义来源与阈值。
config.json - 用户配置，由 .gitignore 排除。
requirements.txt - 可选邮件 HTML 渲染依赖 markdown>=3.5。
.gitignore - 排除配置、凭证、状态与生成报告。
README.md - 英文产品说明与运行指南。
README.zh-CN.md - 中文产品说明与运行指南。
LICENSE - MIT 许可。
</config>

## 运行边界

包版本为 0.1.0，未提供 Web 服务与前端。
`python -m radar sources` 运行 X 与 HF 信号。
`python -m radar daily` 运行每日汇总与复盘。
两类任务共享 state/radar.db 与压缩快照。
分开调度时，daily 使用 `--skip x,hf`。

数据流：采集 → 提词 → 合并 → 名字评分 → 报告与入库。
新词表：当天名字 → 取证与提词 → 相关性筛选 → 搜索量 → Trends 规模 → 决策。
新词表把名字背后的通用词写入同一张表，通用词同样入库。
延迟复盘：到期线索 → Trends 序列 → 结论写回 SQLite。
名字评分判断专有名称，不代表搜索量或商业价值。
命中率来自延迟复盘，不能用模型评分替代。
日搜是估算值，不等于真实搜索次数。

AIsa 汇聚 X、WHOIS、Trends、名字模型与通用词提词。
GoAnyAPI 是可选的第二数据源，只提供相关查询与国家日走势。
HF、GitHub、sitemap 使用公共接口。
GSC 只读取用户已授权站点的曝光查询。
GSC 查询独立展示，不进入候选入库与复盘。
复盘 hit 表示满足上涨规则，提前天数可为负。
密钥使用环境变量，禁止写入公开配置。
付费请求不自动重试，避免重复计费。
没配 GOANYAPI_API_KEY 时，新词表照常产出并标注缺少哪一块。

## 验证与限制

运行测试：`python -m pytest -q tests`。
现有测试覆盖逻辑，不验证真实上游可用性。
README 记录了 WHOIS 参数校验的上游故障。
Actions 缓存丢失会丢失快照与复盘历史。
采集快照先更新，后续入库失败不能自动重放。
各信号分别定义“新”，不保证名称首次公开。
Trends 最后两天未结算，所有日序列读取先剔除。
采集任务默认关闭，需 RADAR_ENABLED=true。

## 上游同步

本仓库跟踪上游 zhuyansen/new-term-radar，其远端名为 upstream。
本地 main 只在上游之上加 GEB 文档提交，不改上游代码。
同步：`git fetch upstream` 后执行 `git rebase upstream/main`。
本地有未提交的文档改动时，先 `git stash`，rebase 后再 `git stash pop`。
L3 契约写在模块 docstring 之上，与上游 docstring 分层，便于合并。
上游改动某文件后，必须复核该文件的 L3 契约。

## 文档回环

进入模块前读取该目录的 CLAUDE.md。
变更文件时核对 INPUT/OUTPUT/POS 契约。
文件或接口变化时同步模块成员清单。
顶级结构变化时同步本地图。

法则: 极简·稳定·导航·版本精确
