---
project: feed-tools
date: 2026-11-02
title: 空 feed 格式样例
---

# 格式样例

未使用 Problem / Decision / Change 或「问题 / 决策 / 变更」标题的段落不会变成事实。

## 问题

解析器遇到空 feed 时会跳过该条目，避免写入空白摘要。

## 决策

保留跳过行为，并把依据写进 changelog。

## 证据

- changelog: 解析器遇到空 feed 时会跳过该条目，避免写入空白摘要。保留跳过行为，并把依据写进 changelog。
- url: https://docs.python.org/3/library/html.parser.html
