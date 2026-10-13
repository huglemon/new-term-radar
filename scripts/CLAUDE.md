# scripts/
> L2 | 父级: ../CLAUDE.md

成员清单
gsc_auth.py: 本机运行 Google 只读 OAuth 授权，生成 GSC 刷新凭证；运行时可选依赖 google-auth-oauthlib。

凭证写到当前工作目录，由 .gitignore 排除。
雷达通过 radar/gsc.py 读取凭证。

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
