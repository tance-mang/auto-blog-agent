"""Resolve writing language from explicit preference or user-provided blog samples.

Never infer language from IP, location, timezone or the profile template.
"""
import json
import re
from collections import Counter


def detect(text):
    text = re.sub(r'```.*?```|<[^>]+>|https?://\S+', ' ', text, flags=re.S)
    han = len(re.findall(r'[\u4e00-\u9fff]', text))
    latin = len(re.findall(r'[A-Za-z]', text))
    if han >= 40 and han / max(han + latin, 1) > .25:
        return 'zh'
    # Latin script alone cannot distinguish English from French, etc.
    words = re.findall(r'\b[a-z]+\b', text.lower())
    if len(words) >= 50 and sum(w in {'the', 'and', 'is', 'of', 'to', 'in', 'for', 'with', 'a'} for w in words) >= 12:
        return 'en'
    return None


def resolve(settings, state, root, override=None):
    chosen = override or settings.get('content', 'auto')
    if chosen != 'auto':
        if not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*', chosen):
            raise ValueError('Use a language tag such as en, zh-CN or fr')
        return chosen
    record = state / 'language.json'
    if record.exists():
        return json.loads(record.read_text(encoding='utf-8'))['language']
    samples = root / 'private/language-samples'
    votes = Counter(filter(None, (detect(p.read_text(encoding='utf-8')) for p in sorted(samples.glob('*.md'))[-10:])))
    if not votes:
        raise ValueError('Language uncertain: set language.content or supply article-body samples in private/language-samples/*.md')
    language, count = votes.most_common(1)[0]
    if count / sum(votes.values()) < .8:
        raise ValueError('Mixed-language blog: configure language.content for this run')
    state.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({'language': language, 'basis': 'user-provided article samples', 'votes': dict(votes)}), encoding='utf-8')
    return language
