# 第三方来源与致谢

当前项目代码为新编写，未复制其他博客 Agent 项目的代码。

运行依赖（通过 pip 安装，未将其源码打包进仓库）：

| 项目 | 用途 | 许可证与来源 |
|---|---|---|
| feedparser | RSS/Atom 解析 | BSD-2-Clause；https://github.com/kurtmckee/feedparser/blob/main/LICENSE |
| PyYAML | YAML 配置与 Front Matter | MIT；https://github.com/yaml/pyyaml/blob/main/LICENSE |
| tzdata | 跨平台时区数据 | Apache-2.0，时区数据另有授权；https://github.com/python/tzdata |

设计调研参考：https://github.com/Dogacel/agent-blog 。仅参考“自动发现素材并生成博客”的思路，不复制其代码和文档。

GitHub Actions 调度行为参考：https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule 。定时运行可能延迟，公开仓库长期无活动时可能停用。

后续引入第三方代码时，需记录具体文件、上游版本、修改范围，并保留上游要求的版权与许可证。仅在 README 署名不能替代许可证要求。
