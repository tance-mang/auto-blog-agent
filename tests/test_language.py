import tempfile
import unittest
from pathlib import Path
from autoblog.language import resolve

class LanguageTests(unittest.TestCase):
    def test_explicit_beats_saved(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertEqual(resolve({'content': 'zh-CN'}, root, root, 'en'), 'en')

    def test_uncertain_does_not_guess(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                resolve({'content': 'auto'}, Path(d), Path(d))

    def test_samples_are_remembered(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            samples = root / 'private/language-samples'
            samples.mkdir(parents=True)
            article = samples / '2026-11-04.md'
            article.write_text('这是个人博客的正文资料与开发记录。' * 20, encoding='utf-8')
            self.assertEqual(resolve({}, root / 'state', root), 'zh')
            article.unlink()
            self.assertEqual(resolve({}, root / 'state', root), 'zh')
