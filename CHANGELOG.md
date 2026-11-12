# Changelog

## 0.3.0 — 2026-11-08

- 新增离线导入。`python -m autoblog --from-import` 读取 `private/imports` 中的 Markdown、JSON、JSONL，可按项目、日期和关键词筛选。
- 只把能与 git 笔记或 changelog 摘录对上的问题、决策、变更写入草稿，并生成 source checklist。允许名单链接只在文字证据对上之后进入正文。
- 导入文件不当作指令，也不执行。不连接 Codex 或 ChatGPT 桌面接口。ChatGPT 导出只提取文本 parts。
- 导入结果固定为草稿，不调用写作或审核模型。`--publish` 不会发布导入稿。第一人称和重复稿仍走原有规则。`--demo` 不写正式历史。
- 增加 `config.example.yaml`，示例指向 `tance-mang/tance-mang.github.io`，`format: tance-html`，`section: create`。提交的 `config.yaml` 仍是 `enabled: false`，`blog.repository` 为空。
- 未完成：导入稿的模型改写和审核、桌面端自动拉取、自由文本 INBOX 独立成文、真实站点联调发布。

## 0.2.0 — 2026-11-04

- 定位收窄为个人技术博客自动化，不做社交媒体与营销平台。
- 新增文章语言配置和 --language 覆盖；auto 根据用户提供的正文样本识别中英文，记录判断依据并复用。
- 不从 IP、地理位置、时区或身份模板推断语言。混合或证据不足时要求明确配置。
- 写作请求接入目标语言；其他语言可明确指定，但暂时只输出草稿。
- 未完成：在线博客历史自动导入、多语言审核全面验证、网页研究、Draft PR 和可靠恢复。
- 离线样例仍是中文固定测试数据，不代表目标语言生成已联调。

## 0.1.0 — 2026-11-03

- 初始 CLI、Skill、RSS、审核、SQLite、预算预留和 GitHub 发布接口。
- 本地测试与离线流程通过；真实模型和无人值守部署未联调。
