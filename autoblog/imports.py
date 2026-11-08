"""Offline drafts from chat and work-log files the user placed on disk.

File contents are untrusted data. This module does not execute them, does not
treat them as instructions, and does not contact desktop chat applications.
"""
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path


MAX_BYTES = 8_000_000
MAX_FACTS = 40
FACT_MAX = 1000
EVIDENCE_MAX = 2000
NOTES = (
    'File contents were treated as data and were not executed.',
    'No desktop chat API was called.',
)
SECTION_LABELS = (('problem', '问题'), ('decision', '决策'), ('change', '变更'))
FACT_KINDS = {
    'problem': 'problem', '问题': 'problem',
    'decision': 'decision', '决策': 'decision', '决定': 'decision',
    'change': 'change', '变更': 'change', '改动': 'change',
}
HEADINGS = dict(FACT_KINDS, evidence='evidence', 证据='evidence')
GENERIC = {
    'this', 'that', 'with', 'from', 'have', 'were', 'http', 'https', 'html', 'index',
    'file', 'data', 'true', 'false', 'null', 'note', 'text', 'kind', 'www',
    '问题', '决策', '决定', '变更', '改动', '证据', '记录', '材料', '文章',
    '我们', '这个', '一个', '可以', '没有', '不是', '因为', '所以',
}
INSTRUCTION = re.compile(
    r'(ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions'
    r'|disregard\s+(?:the\s+)?(?:above|previous)\s+(?:rules|instructions)'
    r'|忽略(?:之前|以上|前面|全部|所有)的?(?:指令|规则|提示|限制)'
    r'|不要遵守'
    r'|你现在是'
    r'|__import__'
    r'|os\.system'
    r'|subprocess\.'
    r'|\beval\s*\('
    r'|\bexec\s*\('
    r'|<\s*script\b)',
    re.I,
)
URL_RE = re.compile(r'https?://[^\s)\]>\'"]+')
INTRO = (
    '本文整理用户授权放入导入目录的聊天记录或工作记录。'
    '正文只保留能与本次一并提供的 git 笔记、changelog 摘录，或允许名单中的链接相对应的问题、决策与变更。'
    '没有对上证据的候选事实只出现在 source checklist，不写成正文结论。'
    '整理时不运行材料里的命令或代码，不补充材料以外的测试结果、身份、经历、观点或引用。'
    '带有个人口吻的句子、以及尚未实际运行核对的教程，会继续保持草稿。'
    '导入文件里的提示语只作为数据保存，不会被当成新的操作指令。'
    '草稿只供人工继续审阅。当前这条导入路径不会自动发布，也不会覆盖博客上已经存在的文章。'
)


def resolve_import_dir(root, relative):
    relative = 'private/imports' if relative in (None, '') else str(relative)
    posix = relative.replace('\\', '/')
    if posix.startswith('/') or '..' in Path(posix).parts:
        raise ValueError('imports path must stay inside the repository')
    path = (root / relative).resolve()
    root_resolved = root.resolve()
    if path != root_resolved and root_resolved not in path.parents:
        raise ValueError('imports path must stay inside the repository')
    if path.exists() and not path.is_dir():
        raise ValueError('imports path is not a directory')
    return path


def prepare_import(imports_dir, inbox=None, *, project='', since='', until='', keywords=None, url_allowed=None):
    project = _optional_text(project, 'import project')
    since = _optional_day(since, 'import since')
    until = _optional_day(until, 'import until')
    if since and until and since > until:
        raise ValueError('import since is after until')
    keywords = _keywords(keywords)
    allow = url_allowed or (lambda url: False)
    loaded = _load_dir(imports_dir)
    inbox_records = _load_inbox(inbox)
    accepted = list(loaded['accepted_files'])
    if inbox_records:
        accepted.append('INBOX.md')
    base = _checklist(project, since, until, keywords, accepted, loaded['skipped'], [], [])
    if not accepted and not loaded['skipped']:
        return {'status': 'skip', 'reason': 'empty import', 'checklist': None}
    records = loaded['records'] + inbox_records
    if not records:
        reason = 'no readable import files' if loaded['skipped'] and not loaded['accepted_files'] else 'no candidate facts'
        return {'status': 'skip', 'reason': reason, 'checklist': base}
    filtered = _filter_records(records, project, since, until, keywords)
    base['records_loaded'] = len(records)
    base['records_after_filter'] = len(filtered)
    if not filtered:
        return {'status': 'skip', 'reason': 'no import matched filters', 'checklist': base}
    correlated, dropped, urls = _correlate(filtered, allow)
    checklist = _checklist(project, since, until, keywords, accepted, loaded['skipped'], correlated, dropped, urls)
    checklist['records_loaded'] = len(records)
    checklist['records_after_filter'] = len(filtered)
    if not correlated:
        return {'status': 'skip', 'reason': 'no corroborated import facts', 'checklist': checklist}
    article, topic, ident = _render(correlated)
    return {
        'status': 'ok', 'reason': '', 'article': article, 'topic': topic,
        'ident': ident, 'checklist': checklist,
    }


def _optional_text(value, field):
    if value in (None, ''):
        return ''
    if isinstance(value, str):
        return value.strip()
    raise ValueError(f'{field} must be a string')


def _optional_day(value, field):
    if value in (None, ''):
        return ''
    parsed = _parse_day(value)
    if not parsed:
        raise ValueError(f'{field} must be YYYY-MM-DD')
    return parsed


def _keywords(value):
    if value in (None, ''):
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(',') if part.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    raise ValueError('import keywords must be a list')


def _parse_day(value):
    if value in (None, '', False):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
            datetime.strptime(text, '%Y-%m-%d')
            return text
        if re.match(r'\d{4}-\d{2}-\d{2}', text):
            try:
                return datetime.fromisoformat(text.replace('Z', '+00:00')).date().isoformat()
            except ValueError:
                return None
    return None


def _checklist(project, since, until, keywords, files, skipped, correlated, dropped, urls=None):
    urls = urls or {'accepted': [], 'rejected': []}
    return {
        'version': 1,
        'filters': {'project': project, 'since': since, 'until': until, 'keywords': keywords},
        'files': files,
        'skipped_files': skipped,
        'correlated': correlated,
        'dropped': dropped,
        'urls': urls,
        'notes': list(NOTES),
    }


def _load_dir(directory):
    result = {'records': [], 'accepted_files': [], 'skipped': []}
    if directory is None or not Path(directory).exists():
        return result
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError('imports path is not a directory')
    root = directory.resolve()
    paths = []
    for path in directory.rglob('*'):
        if not path.is_file() or path.is_symlink() or path.name.startswith('.'):
            continue
        resolved = path.resolve()
        if root not in resolved.parents:
            continue
        paths.append(path)
    for path in sorted(paths, key=lambda item: item.as_posix()):
        rel = path.relative_to(directory).as_posix()
        lower = path.name.lower()
        if lower.endswith(('.git-note.md', '.changelog.md', '.evidence.json')):
            continue
        if not lower.endswith(('.md', '.json', '.jsonl')):
            continue
        try:
            text = _read_limited(path)
            records = _parse_file(text, rel, lower)
        except UnicodeDecodeError:
            result['skipped'].append({'path': rel, 'reason': 'not utf-8'})
            continue
        except ValueError as exc:
            result['skipped'].append({'path': rel, 'reason': str(exc)})
            continue
        result['accepted_files'].append(rel)
        result['records'].extend(records)
    _attach_sidecars(result['records'], directory)
    return result


def _load_inbox(inbox):
    if inbox is None:
        return []
    inbox = Path(inbox)
    if not inbox.is_file() or inbox.is_symlink():
        return []
    try:
        text = _read_limited(inbox)
    except (UnicodeDecodeError, ValueError, OSError):
        return []
    return _parse_file(text, 'INBOX.md', 'inbox.md')


def _read_limited(path):
    data = Path(path).read_bytes()
    if len(data) > MAX_BYTES:
        raise ValueError('file exceeds size limit')
    return data.decode('utf-8-sig')


def _parse_file(text, source, lower_name):
    if lower_name.endswith('.jsonl'):
        return _load_jsonl(text, source)
    if lower_name.endswith('.json'):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError('invalid json') from exc
        if isinstance(payload, list):
            if payload and all(_is_message(item) for item in payload):
                return _record_from_obj({'messages': payload}, source)
            records = []
            for item in payload:
                records.extend(_record_from_obj(item, source))
            return records
        return _record_from_obj(payload, source)
    return _markdown_records(text, source)


def _load_jsonl(text, source):
    rows = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f'invalid jsonl line {lineno}') from exc
    dicts = [row for row in rows if isinstance(row, dict)]
    if dicts and all(_is_message(row) for row in dicts):
        return _record_from_obj({'messages': dicts}, source)
    records = []
    for row in dicts:
        records.extend(_record_from_obj(row, source))
    return records


def _is_message(value):
    return isinstance(value, dict) and ('content' in value or 'role' in value) and not any(
        key in value for key in ('facts', 'evidence', 'messages', 'mapping'))


def _record_from_obj(obj, source):
    if not isinstance(obj, dict):
        return []
    if 'messages' not in obj and 'mapping' not in obj and _is_message(obj):
        obj = {
            'project': obj.get('project'),
            'date': obj.get('date') or obj.get('timestamp') or obj.get('create_time'),
            'title': obj.get('title'),
            'messages': [obj],
        }
    if isinstance(obj.get('messages'), list):
        messages = [item for item in obj['messages'] if isinstance(item, dict)]
    elif isinstance(obj.get('mapping'), dict):
        messages = _messages_from_mapping(obj['mapping'])
    else:
        messages = []
    facts = _explicit_facts(obj.get('facts'))
    evidence = _explicit_evidence(obj.get('evidence'))
    for message in messages:
        if _message_role(message) in {'system', 'tool', 'developer'}:
            continue
        extracted, found = _extract_prose(_content_text(message.get('content')))
        facts.extend(extracted)
        evidence.extend(found)
    facts = _dedupe(facts, ('kind', 'text'))
    evidence = _dedupe(evidence, ('kind', 'text', 'url'))
    if not facts and not evidence:
        return []
    project = obj.get('project') if isinstance(obj.get('project'), str) else ''
    if not project.strip():
        for message in messages:
            candidate = message.get('project')
            if isinstance(candidate, str) and candidate.strip():
                project = candidate
                break
    date_value = _parse_day(obj.get('date') or obj.get('created') or obj.get('create_time') or obj.get('timestamp'))
    if date_value is None:
        for message in messages:
            date_value = _parse_day(message.get('timestamp') or message.get('date') or message.get('create_time'))
            if date_value:
                break
    title = obj.get('title') if isinstance(obj.get('title'), str) else ''
    return [{
        'source': source,
        'project': project.strip(),
        'date': date_value,
        'title': title.strip(),
        'facts': facts,
        'evidence': evidence,
        'raw_text': json.dumps(obj, ensure_ascii=False)[:MAX_BYTES],
    }]


def _messages_from_mapping(mapping):
    messages = []
    for node in mapping.values():
        if not isinstance(node, dict) or not isinstance(node.get('message'), dict):
            continue
        message = node['message']
        author = message.get('author') if isinstance(message.get('author'), dict) else {}
        text = _content_text(message.get('content'))
        if not text.strip():
            continue
        messages.append({
            'role': author.get('role') or '',
            'content': text,
            'create_time': message.get('create_time') or node.get('create_time'),
        })
    messages.sort(key=lambda item: item.get('create_time') or 0)
    return messages


def _message_role(message):
    role = message.get('role')
    if not isinstance(role, str) and isinstance(message.get('author'), dict):
        role = message['author'].get('role')
    return role.strip().lower() if isinstance(role, str) else ''


def _content_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return '\n'.join(part for part in value if isinstance(part, str))
    if isinstance(value, dict):
        parts = value.get('parts')
        if isinstance(parts, list):
            return '\n'.join(part for part in parts if isinstance(part, str))
        if isinstance(value.get('text'), str):
            return value['text']
    return ''


def _explicit_facts(value):
    facts = []
    if not isinstance(value, list):
        return facts
    for item in value:
        if isinstance(item, str):
            parsed = _match_fact_line(item)
            if parsed:
                facts.append(parsed)
        elif isinstance(item, dict):
            kind = FACT_KINDS.get(str(item.get('kind') or item.get('type') or '').strip().lower())
            text = item.get('text') if isinstance(item.get('text'), str) else item.get('content')
            text = _clean(text, FACT_MAX) if isinstance(text, str) else ''
            if kind and text:
                facts.append({'kind': kind, 'text': text})
    return facts


def _explicit_evidence(value):
    items = value if isinstance(value, list) else []
    evidence = []
    for item in items:
        if isinstance(item, str):
            parsed = _match_evidence_line(item)
            if parsed:
                evidence.append(parsed)
            continue
        if not isinstance(item, dict):
            continue
        kind = _evidence_kind(item.get('kind') or item.get('type') or '')
        text = item.get('text') if isinstance(item.get('text'), str) else item.get('content')
        text = text if isinstance(text, str) else ''
        url = item.get('url') if isinstance(item.get('url'), str) else ''
        if not kind:
            kind = 'url' if url.strip() else ('git_note' if text.strip() else '')
        if not kind:
            continue
        entry = {'kind': kind, 'text': _clean(text, EVIDENCE_MAX), 'url': url.strip()}
        supports = item.get('supports')
        if isinstance(supports, str):
            supports = [supports]
        if isinstance(supports, list):
            entry['supports'] = [part.strip() for part in supports if isinstance(part, str) and part.strip()]
        evidence.append(entry)
    return evidence


def _markdown_records(text, source):
    meta, body = _front_matter(text)
    facts, evidence = _extract_prose(body)
    facts = _dedupe(facts, ('kind', 'text'))
    evidence = _dedupe(evidence, ('kind', 'text', 'url'))
    if not facts and not evidence:
        return []
    return [{
        'source': source,
        'project': (meta.get('project') or '').strip(),
        'date': _parse_day(meta.get('date')),
        'title': (meta.get('title') or '').strip(),
        'facts': facts,
        'evidence': evidence,
        'raw_text': text[:MAX_BYTES],
    }]


def _front_matter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return {}, text
    meta = {}
    for index, line in enumerate(lines[1:], 1):
        if line.strip() == '---':
            return meta, '\n'.join(lines[index + 1:])
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        meta[key.strip().lower()] = value.strip().strip('"').strip("'")
    return {}, text


def _extract_prose(body):
    facts, evidence, section, paragraph = [], [], None, []

    def flush():
        nonlocal paragraph
        text = _clean(' '.join(paragraph), FACT_MAX)
        paragraph = []
        if not text:
            return
        if section in {'problem', 'decision', 'change'}:
            labeled = _match_fact_line(text)
            facts.append(labeled or {'kind': section, 'text': text})
        elif section == 'evidence':
            evidence.extend(_evidence_from_text(text))

    for raw in body.splitlines():
        line = raw.strip()
        heading = _match_heading(line)
        if heading:
            flush()
            section = heading
            continue
        if not line:
            flush()
            continue
        fact = _match_fact_line(line)
        found = None if fact else _match_evidence_line(line)
        if fact or found or (section in {'problem', 'decision', 'change'} and re.match(r'[-*]\s+', line)):
            flush()
        if fact:
            facts.append(fact)
            continue
        if found:
            evidence.append(found)
            continue
        if section in {'problem', 'decision', 'change'} and re.match(r'[-*]\s+', line):
            facts.append({'kind': section, 'text': _clean(re.sub(r'^[-*]\s+', '', line), FACT_MAX)})
            continue
        if section == 'evidence' and line.lstrip('-* ').startswith(('http://', 'https://')):
            evidence.extend(_evidence_from_text(line))
            continue
        if section in {'problem', 'decision', 'change', 'evidence'}:
            paragraph.append(line)
    flush()
    return facts, evidence


def _match_heading(line):
    match = re.match(r'^#{1,6}\s+(.+?)\s*$', line)
    if not match:
        return None
    return HEADINGS.get(match.group(1).strip().lower())


def _match_fact_line(line):
    line = re.sub(r'^[-*]\s+', '', line.strip())
    match = re.match(r'^(problem|问题|decision|决策|决定|change|变更|改动)\s*[:：]\s*(.+)$', line, re.I)
    if not match:
        return None
    kind = FACT_KINDS.get(match.group(1).lower())
    text = _clean(match.group(2), FACT_MAX)
    if not kind or not text:
        return None
    return {'kind': kind, 'text': text}


def _match_evidence_line(line):
    line = re.sub(r'^[-*]\s+', '', line.strip())
    match = re.match(
        r'^(git(?:[\s_-]*note)?|笔记|changelog|change[\s_-]*log|变更日志|url|link|链接)\s*[:：]\s*(.+)$',
        line, re.I)
    if not match:
        return None
    kind = _evidence_kind(match.group(1))
    text = _clean(match.group(2), EVIDENCE_MAX)
    if not kind or not text:
        return None
    urls = URL_RE.findall(text)
    return {'kind': kind, 'text': text, 'url': urls[0] if kind == 'url' and urls else ''}


def _evidence_kind(token):
    key = str(token or '').strip().lower().replace(' ', '').replace('_', '').replace('-', '')
    return {
        'git': 'git_note', 'gitnote': 'git_note', '笔记': 'git_note',
        'changelog': 'changelog', '变更日志': 'changelog',
        'url': 'url', 'link': 'url', '链接': 'url',
    }.get(key, '')


def _evidence_from_text(text):
    found = []
    for line in text.splitlines() or [text]:
        parsed = _match_evidence_line(line)
        if parsed:
            found.append(parsed)
            continue
        for url in URL_RE.findall(line):
            found.append({'kind': 'url', 'text': _clean(line, EVIDENCE_MAX), 'url': url})
    return found


def _attach_sidecars(records, directory):
    grouped = {}
    for record in records:
        grouped.setdefault(record['source'], []).append(record)
    root = directory.resolve()
    for source, group in grouped.items():
        path = Path(source)
        stem = path.name[:-6] if path.name.endswith('.jsonl') else path.stem
        parent = directory / path.parent
        extra = []
        note = parent / f'{stem}.git-note.md'
        change = parent / f'{stem}.changelog.md'
        payload = parent / f'{stem}.evidence.json'
        if _inside(root, note):
            text = _optional_read(note)
            if text:
                extra.append({'kind': 'git_note', 'text': _clean(text, EVIDENCE_MAX), 'url': ''})
        if _inside(root, change):
            text = _optional_read(change)
            if text:
                extra.append({'kind': 'changelog', 'text': _clean(text, EVIDENCE_MAX), 'url': ''})
        if _inside(root, payload):
            text = _optional_read(payload)
            if text:
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    extra.extend(_explicit_evidence(parsed))
                elif isinstance(parsed, dict):
                    extra.extend(_explicit_evidence(parsed.get('evidence')))
        for record in group:
            record['evidence'].extend(extra)


def _inside(root, path):
    if not path.is_file() or path.is_symlink():
        return False
    resolved = path.resolve()
    return root == resolved.parent or root in resolved.parents


def _optional_read(path):
    try:
        return _read_limited(path)
    except (UnicodeDecodeError, ValueError, OSError):
        return ''


def _filter_records(records, project, since, until, keywords):
    selected = []
    folded = [item.casefold() for item in keywords]
    for record in records:
        if project and record.get('project', '').casefold() != project.casefold():
            continue
        if (since or until) and not record.get('date'):
            continue
        if since and record['date'] < since:
            continue
        if until and record['date'] > until:
            continue
        if folded:
            haystack = '\n'.join([
                record.get('project') or '', record.get('title') or '', record.get('raw_text') or '',
            ]).casefold()
            if not any(keyword in haystack for keyword in folded):
                continue
        selected.append(record)
    return selected


def _correlate(records, allow):
    correlated, dropped = [], []
    accepted, rejected, seen = [], [], set()
    kept = 0
    for record in records:
        for evidence in record.get('evidence') or []:
            for url in _evidence_urls(evidence):
                if url in seen:
                    continue
                seen.add(url)
                if allow(url):
                    accepted.append(url)
                else:
                    rejected.append({'url': url, 'reason': 'url not allowlisted'})
        for fact in record.get('facts') or []:
            entry = {
                'kind': fact['kind'], 'text': fact['text'], 'file': record['source'],
                'project': record.get('project') or '', 'date': record.get('date') or '',
            }
            if INSTRUCTION.search(fact['text']):
                dropped.append({**entry, 'reason': 'ignored instruction'})
                continue
            if kept >= MAX_FACTS:
                dropped.append({**entry, 'reason': 'fact limit exceeded'})
                continue
            matched = [item for item in record.get('evidence') or [] if _correlates(fact['text'], item)]
            if not matched:
                dropped.append({**entry, 'reason': 'no corroborating evidence'})
                continue
            kept += 1
            kinds, urls = [], []
            for item in matched:
                if item.get('kind') and item['kind'] not in kinds:
                    kinds.append(item['kind'])
            # A URL does not corroborate a fact by itself. Once text evidence matches,
            # one allowlisted URL from the same file can be cited.
            for item in record.get('evidence') or []:
                for url in _evidence_urls(item):
                    if allow(url) and url not in urls:
                        urls.append(url)
            correlated.append({**entry, 'evidence_kinds': kinds, 'urls': urls})
    return correlated, dropped, {'accepted': accepted, 'rejected': rejected}


def _evidence_urls(evidence):
    found = []
    raw = (evidence.get('url') or '').strip()
    if raw:
        found.append(raw)
    found.extend(URL_RE.findall(evidence.get('text') or ''))
    unique = []
    for url in found:
        if url not in unique:
            unique.append(url)
    return unique


def _correlates(fact_text, evidence):
    if fact_text in set(evidence.get('supports') or []):
        return True
    blob = ((evidence.get('text') or '') + '\n' + (evidence.get('url') or '')).strip()
    if len(fact_text) >= 8 and fact_text in blob:
        return True
    quoted = (evidence.get('text') or '').strip()
    if len(quoted) >= 8 and quoted in fact_text:
        return True
    overlap = _tokens(fact_text) & _tokens(blob)
    if any(re.fullmatch(r'[a-z0-9][a-z0-9_-]{3,}', token) for token in overlap):
        return True
    if any(re.fullmatch(r'[\u4e00-\u9fff]{3,}', token) for token in overlap):
        return True
    return len([token for token in overlap if re.fullmatch(r'[\u4e00-\u9fff]{2}', token)]) >= 2


def _tokens(text):
    found = set()
    for token in re.findall(r'[A-Za-z0-9][A-Za-z0-9_-]{3,}', text.lower()):
        if not token.isdigit():
            found.add(token)
    for run in re.findall(r'[\u4e00-\u9fff]+', text):
        if 2 <= len(run) <= 12:
            found.add(run)
        for size in (2, 3, 4):
            if len(run) < size:
                continue
            for index in range(len(run) - size + 1):
                found.add(run[index:index + size])
    return found - GENERIC


def _render(correlated):
    dates, projects = [], []
    for fact in correlated:
        if fact.get('date') and fact['date'] not in dates:
            dates.append(fact['date'])
        if fact.get('project') and fact['project'] not in projects:
            projects.append(fact['project'])
    lines = [INTRO, '']
    meta = []
    if dates:
        meta.append('材料日期：' + '、'.join(dates) + '。')
    if projects:
        meta.append('项目：' + '、'.join(projects) + '。')
    if meta:
        lines.extend([''.join(meta), ''])
    primary = ''
    for fact in correlated:
        for url in fact.get('urls') or []:
            primary = url
            break
        if primary:
            break
    visible = 0
    for kind, label in SECTION_LABELS:
        items = []
        for fact in correlated:
            if fact['kind'] != kind:
                continue
            shown = _display(fact['text'])
            if shown:
                items.append(shown)
        if not items:
            continue
        visible += len(items)
        lines.append(f'## {label}')
        lines.extend(f'- {item}' for item in items)
        lines.append('')
    if not visible:
        raise ValueError('correlated facts produced no article text')
    if primary:
        lines.append(f'来源链接：{primary}')
    body = '\n'.join(lines).strip() + '\n'
    label = projects[0] if len(projects) == 1 else ('、'.join(projects) if projects else '未命名')
    label = re.sub(r'\s+', ' ', label).strip() or '未命名'
    title = f'导入材料整理：{label}'
    if len(title) > 80:
        title = title[:79] + '…'
    ident = hashlib.sha256(json.dumps(
        {'title': title, 'body': body}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    return (
        {'title': title, 'body': body},
        {'title': title, 'url': primary, 'excerpt': '', 'origin': 'import'},
        ident,
    )


def _display(text):
    return re.sub(r'\s+', ' ', URL_RE.sub(' ', text)).strip()


def _clean(text, limit):
    return re.sub(r'\s+', ' ', str(text or '').replace('\x00', '')).strip()[:limit]


def _dedupe(items, keys):
    seen, unique = set(), []
    for item in items:
        marker = tuple(item.get(key) or '' for key in keys)
        if marker in seen or not any(marker):
            continue
        seen.add(marker)
        unique.append(item)
    return unique
