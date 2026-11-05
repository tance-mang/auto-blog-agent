"""Build a public-safe incident report from a trusted GitHub run."""
import json
import os
import re
import smtplib
import ssl
import subprocess
from email.message import EmailMessage
from pathlib import Path
from .guardian_ai import suggestion

RULES = (
    ("simulation", r"GUARDIAN_DRILL", "演练注入了预期故障", "确认报告产物存在，无需重跑发布。"),
    ("configuration", r"\b(?:BLOG_TOKEN|AI_API_KEY) is required\b", "缺少配置凭据", "检查对应仓库 Secret，确认后再重跑。"),
    ("github_permission", r"Resource not accessible by integration|Write access to repository not granted", "GitHub 拒绝写入", "核对目标仓库、令牌的 Contents 写权限和分支规则。"),
    ("model_configuration", r"Configure AI_API_KEY and writer_model/reviewer_model", "模型配置不完整", "核对模型名称和 Actions 凭据。"),
    ("rate_limit", r"HTTP(?: Error)? 429\b|rate_limit_exceeded", "服务疑似限流", "查看服务配额和重试间隔，确认后再重跑。"),
    ("network", r"TimeoutError|timed out|Temporary failure in name resolution", "网络请求或任务疑似超时", "检查服务状态和网络，再决定是否重跑。"),
)


def diagnose(conclusion, logs):
    if conclusion == "timed_out":
        return "timeout", "GitHub 标记运行超时", "检查各步骤耗时、外部请求与任务超时设置。"
    for code, pattern, reason, action in RULES:
        if re.search(pattern, logs, re.I):
            return code, reason, action
    return "unknown", "证据不足，需人工排查", "从原运行页查看第一个失败步骤，并检查是否已有发布结果。"


def report(repo, run, logs, logs_available):
    run_id = int(run["id"])
    attempt = int(run["run_attempt"])
    conclusion = run["conclusion"]
    if conclusion not in {"failure", "timed_out", "startup_failure", "action_required", "cancelled", "stale"}:
        raise ValueError("Unsupported incident conclusion")
    code, reason, action = diagnose(conclusion, logs)
    return f"""# 自动化故障报告 · {run_id}/{attempt}

| 字段 | 结果 |
| --- | --- |
| GitHub 运行结果 | `{conclusion}` |
| 诊断规则 | `{code}` |
| 失败日志 | {'已用于匹配规则' if logs_available else '暂不可用，按运行状态诊断'} |
| 原运行 | [查看第 {attempt} 次尝试](https://github.com/{repo}/actions/runs/{run_id}/attempts/{attempt}) |

**初步判断**　{reason}

**影响范围**　该次运行异常结束。仅凭运行状态无法确定内容是否已发布。

**处理建议**　{action} 重跑发布前，先核对目标站点或目标仓库，防止重复发布。
"""


def send_email(body):
    msg = EmailMessage()
    msg["Subject"] = "Auto Blog Agent · 自动化故障"
    msg["From"] = os.environ["SMTP_FROM"]
    msg["To"] = os.environ["SMTP_TO"]
    msg.set_content(body)
    with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], 465, context=ssl.create_default_context(), timeout=20) as smtp:
        smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)


def main():
    if os.environ.get("GUARDIAN_SEND_MAIL") == "1":
        send_email(Path("incident.md").read_text(encoding="utf-8"))
        return
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    run = event["workflow_run"]
    repo = os.environ["GITHUB_REPOSITORY"]
    try:
        result = subprocess.run(
            ["gh", "run", "view", str(int(run["id"])), "--repo", repo,
             "--attempt", str(int(run["run_attempt"])), "--log-failed"],
            capture_output=True, timeout=60, encoding="utf-8", errors="replace",
        )
        logs = result.stdout if result.returncode == 0 else ""
    except subprocess.TimeoutExpired:
        logs = ""
    body = report(repo, run, logs, bool(logs.strip()))
    if diagnose(run["conclusion"], logs)[0] == "unknown":
        extra = suggestion(run["conclusion"], logs)
        if extra:
            text = re.sub(r"[^\w\s，。；：、？！（）-]", " ", extra)
            body += f"\n**AI 排查建议（待验证）**　{text}\n"
    Path("incident.md").write_text(body, encoding="utf-8")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
        summary.write(body)


if __name__ == "__main__":
    main()
