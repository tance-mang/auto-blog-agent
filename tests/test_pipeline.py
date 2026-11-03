import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autoblog.__main__ import checks, database, duplicate, model, publish


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = database(Path(self.tmp.name) / 'test.db')
        self.topic = {'url': 'https://docs.python.org/3/'}

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_personal_narrative_is_blocked(self):
        result = checks({'title': 'Python', 'body': '我亲测了这个功能。' * 50 + self.topic['url']}, self.topic, self.db)
        self.assertTrue(any('Personal' in x for x in result))

    def test_unknown_citation_is_blocked(self):
        result = checks({'title': 'Python', 'body': '资料说明。' * 70 + self.topic['url'] + '\nhttps://example.com'}, self.topic, self.db)
        self.assertIn('Unverified extra source links', result)

    def test_history_deduplicates(self):
        self.db.execute('INSERT INTO articles VALUES (?,?,?,?,?)', ('x', 'Python 3.14 release', 'content', 'published', '2026-01-01'))
        self.assertTrue(duplicate(self.db, 'Python 3.14 release'))

    def test_publish_requires_explicit_target(self):
        with self.assertRaises(ValueError):
            publish({'blog': {'repository': 'owner/repo', 'posts_path': '../bad'}}, 'x.md', 'body')

    def test_budget_blocks_before_network(self):
        cfg = dict(writer_model='test', max_output_tokens=100, daily_token_limit=1,
                   input_usd_per_million=1, output_usd_per_million=1, daily_budget_usd=1)
        with patch.dict('os.environ', {'AI_API_KEY': 'test'}), patch('autoblog.__main__.request') as network:
            with self.assertRaises(RuntimeError):
                model(cfg, self.db, '2026-01-01', 'writer', 'system', {})
            network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
