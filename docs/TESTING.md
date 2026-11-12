# 测试与手动验证

自动化测试通过 `python -m unittest discover -s tests -v` 执行。手动验证单独记录，便于区分仓库代码的测试和外部环境的可行性验证。

## 2026-11-06（Asia/Shanghai） · Codex 桌面端读取 ChatGPT 聊天

| 项目 | 记录 |
| --- | --- |
| 类型 | 手动可行性验证 |
| 环境 | Windows 上已登录的 Codex 桌面端 |
| 被测对象 | 桌面端聊天工具，本次没有运行仓库代码或绑定被测提交 |
| 操作 | 通过 `list_threads` 指定 `source=chatgpt`、`mode=history`，选取一个结果，再用 `read_thread` 读取一轮 |
| 实测结果 | 列表返回 ChatGPT 聊天条目，读取工具返回一轮消息。两个调用均未返回错误 |
| 待验证 | Skill 集成、自动筛选闲聊、合并代码证据、生成草稿和 GitHub Actions 运行 |

公开复盘见[博客文章](https://tance-mang.github.io/2026/11/07/chatgpt-to-codex/)。公开记录只保留验证方法和结果。

## 2026-11-08 · 离线导入与 HTML 配置样例

| 项目 | 记录 |
| --- | --- |
| 类型 | 自动化测试，外加一次只读查看站点模板 |
| 命令 | `python3 -m unittest discover -s tests -v`（24 项通过）；`python3 -m autoblog --demo`；`python3 -m autoblog --from-import --demo` |
| 导入结果 | 仓库里没有 `private/imports`，导入命令打印 `SKIP: empty import`，没有生成文章 |
| 发布 | 未向 `tance-mang/tance-mang.github.io` 写入。HTML 发布测试使用假的 GitHub 响应 |
| 未做 | 未调用 Codex 或 ChatGPT 桌面接口，未用真实模型改写导入稿 |

只读核对了站点仓库 `main` 上的 `_template-post.html`、`create.html`、`observe.html` 和 `archives/index.html`：模板占位符仍在，栏目页和归档页各有一处 `entry-list`。这次没有修改该仓库。

## 博客与仓库同步

每次发布与本项目有关的博客，都同步检查项目仓库。已实现的代码和用户可见变化进入对应文件与变更日志，实际跑过的测试和手动验证写入本页。纯设计文章对应的功能仍按规划记录，状态标记为待实现或待验证。完成后分别核对两个仓库的提交。
