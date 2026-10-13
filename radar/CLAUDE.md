# radar/
> L2 | 父级: ../CLAUDE.md

采集模块输出信号结果，由 report 合并候选词。
CLI 串联评分、入库、复盘和报告输出。
store 保存线索历史，snap 保存来源快照。
usecases 把名字背后的通用词做成新词表。

成员清单
__init__.py: 包版本与公共 HTTP User-Agent。
__main__.py: sources/daily 编排、信号错误隔离与文件输出。
aisa.py: AIsa 工具路由和兼容对话接口；禁止付费请求自动重试。
breakout.py: GitHub 新仓库爆发信号，比较平均涨星与快照增量。
config.py: 默认配置合并、语言初始化与已覆盖词判定。
goanyapi.py: 可选第二数据源；提供 Trends 相关查询与国家日走势，无 key 时整体跳过。
gsc.py: OAuth 刷新与 Search Console 新鲜曝光查询。
i18n.py: 共享中英文报告文案与语言选择。
judge.py: 分批调用名字模型，解析专有名称评分。
new_sites.py: 每周查询 WHOIS，以注册、收录与排名阈值筛选新站。
notify.py: Markdown 邮件渲染与 Resend 发送。
report.py: 候选词合并、名字筛选、入库筛选与报告渲染。
review.py: 到期线索 Trends 验证，逐搜索变体判定并保存结论。
sitemaps.py: sitemap 抓取、URL 去重、快照比较与新增词判定。
snap.py: gzip JSON 快照读写，缺失文件返回 None。
sources.py: X 滚动词表与 HF 榜单差分，合并模型基础名。
store.py: SQLite 线索合并、待复盘队列与信号命中统计。
terms.py: 共享停用词、名称提取、按来源计数与涨幅判定。
usecases.py: 通用词信号；取证、提词、相关性筛选、搜索量、Trends 规模与决策，产出新词表。

## 状态与降级

首次采集 X、HF、sitemap 时建立快照。
GitHub 平均涨星判定不依赖前次快照。
名字模型失败时，报告保留无分数候选词。
复盘逐搜索变体请求，避免共享尺度压低小词。
GSC 查询独立展示，不进入候选入库与复盘。
复盘只执行一次，hit 不要求正提前天数。
采集快照先更新，后续入库失败不能自动重放。
Sitemap 最少命中三个新增 URL，无 lift 下限。
信号阈值由配置控制，名称规则针对 AI 领域。
通用词信号失败时，新词表照出并标注不完整。
没配 GOANYAPI_API_KEY 时，新词表跳过相关查询与国家走势。
Trends 最后两天未结算，所有日序列读取先剔除。
每个名字读两次：出现当天一次，三天后一次。

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
