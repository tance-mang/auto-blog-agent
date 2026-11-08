# Auto Blog Agent · AI 自动博客运营 Skill

![Tests](https://github.com/tance-mang/auto-blog-agent/actions/workflows/test.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green)

让 AI 记住你的身份，从可信资料发现选题，写作、审核并按规则发布中文技术博客。支持 Codex、Claude Code 等 Agent Skills 工具，也可通过 Python CLI 与 GitHub Actions 独立运行。

**检索关键词：** AI 博客自动化 · AI 自动写作 · Agent Skill · 智能选题 · 中文技术博客 · GitHub Pages · 自动发布

一个面向中文个人技术博客的 Agent Skill 与 Python 自动化程序。支持身份规则、RSS 选题、来源摘录写作、独立 AI 审核、历史去重、预算限制、Markdown 输出和 GitHub 仓库发布。

默认关闭发布。接入真实模型和博客前，请先完成 Dry Run；当前尚未完成真实模型与真实博客联调。

## 快速开始

需要 Python 3.11+。

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m autoblog --demo
```

离线样例位于 generated/demo，不调用模型，不写入真实历史，也永远不会发布。每次重复运行均可重现。

## 导入聊天与工作记录

程序只读取你放进本仓库的文件，不连接 Codex、ChatGPT 或其他桌面聊天接口。

```bash
mkdir -p private/imports
# 放入 .md / .json / .jsonl，格式见 docs/examples/
python -m autoblog --from-import --demo
```

`private/` 已被 Git 忽略。自由书写的 `private/INBOX.md` 仍只作为 RSS 写作时的上下文；没有「问题 / 决策 / 变更」结构时，它不会单独成文。空目录打印 `SKIP: empty import`。

可选筛选：

- `--import-project`：项目名，忽略大小写，完全匹配。
- `--import-since`、`--import-until`：含边界的 `YYYY-MM-DD`。设置了日期范围时，没有日期的记录会被跳过。
- `--import-keywords`：可重复的子串筛选。默认关闭，也不借用 RSS 的 `keywords`。

正文只保留能与本次 git 笔记或 changelog 摘录对上的问题、决策、变更。文字对上之后，该文件里按出现顺序的第一个允许名单链接可以作为来源链接。多份材料合并时，正文只引用第一份已经对上、并且带有允许名单链接的材料里的那个链接，其余留在清单。不在 `allowed_hosts` 中的链接只留在清单。文件内容是数据：不执行，也不当成新指令。像越狱提示或 `os.system` / `eval` 的句子会记在清单里，不进正文。`system`、`tool`、`developer` 角色不会提升为事实。

输出在 `generated/demo` 或 `generated/live`：Markdown 草稿、`*.checklist.json`、`*.review.json`。导入结果固定 `draft: true`。这条路径不调用写作或审核模型，因此 `--publish` 不会把它发出去。第一人称、未运行的教程、重复稿和缺少来源链接的稿子仍由原有规则拦住。`--demo` 不写入 `state/live`。

单文件约 8MB。ChatGPT 导出只提取 `mapping.message.content.parts` 中的字符串，这不是桌面端接入。同名的 `.git-note.md`、`.changelog.md`、`.evidence.json` 会当作该文件的证据。格式样例见 [docs/examples/import-session.md](docs/examples/import-session.md) 和 [docs/examples/import-session.json](docs/examples/import-session.json)。

尚未实现：导入稿的模型改写、桌面聊天自动拉取、自由文本单独成文。

## 配置真实写作

1. 编辑 memory/PROFILE.md 和 EDITORIAL.md。私人素材放 private/INBOX.md，不提交公开仓库。
2. 修改 config.yaml 中的 feeds、allowed_hosts、keywords、writer_model、reviewer_model。
3. 在环境变量设置 AI_API_KEY 和 AI_BASE_URL。程序不会自动加载 .env；.env.example 仅为字段说明。
4. 设置服务商实际价格和每日预算。未提供使用量时仍保留请求前的保守预算预留；失败请求也占预留额度，次日按时区重置。
5. 执行 `python -m autoblog`，查看 generated/live 下文章和 review.json。

兼容服务必须支持 `/chat/completions`、JSON response_format 和 max_tokens。不同供应商的兼容性需要实测；同一模型可同时担任写作与审核，但审核是单独请求。

## 接入博客

先检查博客仓库的框架、文章目录、Front Matter、分支和构建工作流。不要仅凭项目名称猜测。默认适配器生成通用 YAML Front Matter，需要自行验证主题所需字段。`blog.format: tance-html` 改走静态 HTML 发布，见下文。

配置 blog.repository（owner/repo）、branch、posts_path、layout。设置 BLOG_TOKEN，为目标仓库授予 Contents 写入权限。使用专用 PAT 可使提交触发博客原有 push 构建流程；本项目不替博客创建部署流程。先在测试仓库验证，再接真实博客。

确认 Dry Run 后设置 enabled: true，运行 `python -m autoblog --publish`。文件名使用日期和来源 URL 哈希；API 不携带 SHA，因此拒绝覆盖已有文件。不要手动删除发布记录来重试已有文章。

模式：safe 默认，符合全部规则的资料型文章可发布；auto 当前使用同样的硬规则；manual 只保存草稿。个人叙述和代码教程始终保留草稿，当前尚不支持自动创建 PR。

## GitHub Actions

在仓库 Secrets 配置 AI_API_KEY、BLOG_TOKEN；Variables 配置 AI_BASE_URL（不设置则用默认端点）。编辑并提交模型与博客配置后，才开启 enabled。

工作流每小时第 17 分钟唤醒，程序根据 timezone 和 publish_hour 判断是否到期；每日最多发布一篇。支持手动触发。默认 enabled=false，定时运行不会调用付费模型。

状态通过 Actions cache 保存，草稿保留为 7 天 artifact。缓存可能被驱逐，因此它不是可靠永久存储：长期生产使用前应迁移到私有持久状态仓库或对象存储，并实现远端发布对账。当前不要同时运行本地发布和 Actions；工作流 concurrency 只保护工作流内部并发。

## 审核与失败处理

程序检查来源链接、第一人称、部分密钥模式、长度和文本相似度；模型独立检查身份、事实支持、相关性与质量。程序规则属于保守拦截，不能保证识别所有虚构或秘密。来源正文目前使用 RSS 摘录，不抓取和核对完整网页；摘录不足时模型应拒绝。

只重试读取请求，避免模型重复收费。错误输出省略服务商响应正文。生成失败以非零状态结束；审核不通过保存草稿。预算在请求前写入 SQLite。发布成功到历史落库之间仍存在故障窗口；远端已有文件将拒绝覆盖，可能需要人工对账。

## Skill 安装

将仓库完整复制到支持 Agent Skills 的工具技能目录，例如 `~/.codex/skills/auto-blog-agent/` 或 Claude Code 项目 `.claude/skills/auto-blog-agent/`。保留 SKILL.md、程序、配置与 memory 目录；依赖安装到调用工具使用的 Python 环境。其他 AI 工具也可直接阅读 SKILL.md 并运行 CLI，但不能保证所有工具自动识别同一种技能目录。

## 已实现与后续

已实现：端到端离线样例、真实 API 接口、RSS 筛选、独立审核、规则拦截、SQLite 历史、文本去重、预算预留、Markdown、GitHub Contents 发布、`tance-html` 单次提交发布、调度模板，以及从 `private/imports` 生成离线草稿和来源清单。

待实现：桌面聊天自动拉取、导入稿的模型改写与独立审核、自由文本 INBOX 独立成文、完整网页证据提取与声明核对、语义去重、按比例选题、持久远端状态与恢复、PR 审核、`tance-html` 以外的框架适配、周报及封面。未将这些功能包装成已完成能力。导入草稿当前不能直接发布。

第三方依赖和参考来源见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。项目使用 MIT 许可证。


## 项目与 AI 协作

项目发起与维护：[tance-mang](https://github.com/tance-mang)。

本项目由维护者提出需求并与 **OpenAI Codex** 协作完成架构、代码、测试和文档。AI 协作不代表 OpenAI 官方项目、认证或背书。相关提交使用 `Co-authored-by: Codex <noreply@openai.com>` 标记实际协作。


## 个人博客定位与语言习惯（0.2.0）

专注个人技术博客，不扩展到社交媒体运营或通用内容平台。版本变化见 [CHANGELOG.md](CHANGELOG.md)，规划见 [ROADMAP.md](ROADMAP.md)。

文章语言按 `--language`、`language.content`、已保存识别结果、用户提供的正文样本依次确定。不使用 IP、地理位置或时区推断语言，交流语言也不自动替代博客语言。现有中文示例配置保留 `zh-CN`；其他用户应配置自己的身份与编辑规则。

设置 `language.content: auto` 后，将纯文章正文放到 `private/language-samples/*.md`（建议使用日期文件名）。首次运行保守识别中文或英文，将依据保存在 `state/live/language.json`；结果不明确时要求配置。改变长期偏好可明确修改配置；重新识别需先备份并移除该记录。

例如：`python -m autoblog --language en`。其他语言允许明确配置，但尚未验证专属审核规则，因此仅生成草稿。固定离线 demo 仍使用中文；真实多语言生成尚未联调。完整博客历史自动导入、网页研究、Draft PR、发布恢复与风格反馈仍为后续任务。

## 无人值守故障诊断

Auto Blog Agent 负责写作、审核和发布，也是独立开源项目 [Workflow Guardian](https://github.com/tance-mang/workflow-guardian) 的首个接入案例。博客仓库的独立监测工作流直接调用 Guardian Action，并启用博客扩展规则。故障诊断、报告、可选 AI 排查和 SMTP 通知由 Guardian 提供。

- 在 Actions 的 **Workflow Guardian** 运行中查看诊断报告。手动运行 **Guardian drill** 可以注入可复现的失败；演练不发布文章，也不发送邮件。
- **Guardian schedule check** 使用 `GUARDIAN_WATCH_WORKFLOW` 和 `GUARDIAN_MAX_AGE_MINUTES`（默认 180）检查漏跑。
- 可选邮件配置继续读取 `GUARDIAN_EMAIL_ENABLED` 和 `GUARDIAN_SMTP_*` Secrets。可选 AI 读取 `GUARDIAN_AI_KEY` Secret 与 `GUARDIAN_AI_MODEL` Variable。具体说明见 [Guardian 文档](https://github.com/tance-mang/workflow-guardian#在-github-actions-中接入)。

## 静态 HTML 发布

目标站点是 [tance-mang.github.io](https://tance-mang.github.io/)，仓库 `tance-mang/tance-mang.github.io`。[config.example.yaml](config.example.yaml) 写了 `format: tance-html`、`section: create`、`branch: main`，并且 `enabled: false`。程序不读取这个示例文件。提交的 [config.yaml](config.yaml) 保持 `enabled: false`，`blog.repository` 为空，因此这份检出不能直接发布。`section` 也可以改成 `observe`。

`tance-html` 要求站点根目录有 `_template-post.html`，以及对应栏目页和 `archives/index.html`。同一天同一栏目使用固定路径 `{YYYY}/{MM}/{DD}/auto-create/index.html` 或 `auto-observe`。文章和栏目页、归档页的导航在同一次提交中更新，更新 ref 时 `force` 为 false。该路径或导航链接已经存在时，这次发布会停住，不覆盖站内已有文章。

`AI_API_KEY`、`AI_BASE_URL` 和 `BLOG_TOKEN` 只放环境变量。`BLOG_TOKEN` 需要对目标仓库的 Contents 写权限。不要把令牌写进配置文件。

建议顺序：

1. `python -m autoblog --demo`。有本地材料时再跑 `python -m autoblog --from-import --demo`。这两步都不发布。
2. 把示例里需要的 `blog` 字段抄进本地 `config.yaml`，填上 `writer_model` 和 `reviewer_model`。先保持 `enabled: false`。
3. `python -m autoblog`，查看 `generated/live` 的文章和 `review.json`。
4. 只有规则通过、你接受这篇资料型文章之后，才在本地把 `enabled` 改成 `true`。不要把这个改动提交上去。
5. `python -m autoblog --publish`。`safe` 模式下，个人叙述和代码教程仍是草稿。导入草稿当前也不会发布。

先用测试仓库确认 Contents 写入，再把 `repository` 指到真实站点。真实模型和真实博客尚未联调。

项目采用 MIT 许可，由 tance-mang 发起，OpenAI Codex 协作实现与验证。[GitHub Issues](https://github.com/tance-mang/auto-blog-agent/issues) · [QQ 邮箱](mailto:2123759705@qq.com) · [Gmail](mailto:tance.hub@gmail.com)

测试范围与博客同步规则见 [测试与手动验证](docs/TESTING.md)。
