"""Regression checks: never contact Instagram or publish real posts."""
import contextlib
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(os.environ.get('PUBLISHER_PATH', str(Path(__file__).with_name('dasu.py'))))
spec = importlib.util.spec_from_file_location('publisher', MODULE)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


def row(n=1, **extra):
    return {'番号': n, '動画': f'{n}.mp4', '日': '2020-01-01', '本文': 'test', **extra}


class Guards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.getcwd()
        os.chdir(self.tmp.name)
        self.env = patch.dict(os.environ, {'GITHUB_ACTIONS': ''})
        self.env.start()
        self.out = contextlib.redirect_stdout(io.StringIO())
        self.out.__enter__()
        self.post = patch.object(publisher, 'dasu', return_value='test-id')
        self.mock = self.post.start()

    def tearDown(self):
        self.post.stop()
        self.out.__exit__(None, None, None)
        self.env.stop()
        os.chdir(self.old)
        self.tmp.cleanup()

    def schedule(self, rows):
        Path('yotei.json').write_text(json.dumps({'予定': rows}), encoding='utf-8')

    def test_duplicate_rows_and_rerun_publish_once(self):
        self.schedule([row(), row()])
        publisher.main()
        publisher.main()
        self.assertEqual(self.mock.call_count, 1)

    def test_prior_post_anywhere_blocks_earlier_row(self):
        self.schedule([row(), row(投稿ID='existing')])
        publisher.main()
        self.mock.assert_not_called()

    def test_pending_anywhere_blocks_all_copies(self):
        self.schedule([row(), row(要確認='uncertain')])
        publisher.main()
        self.mock.assert_not_called()

    def test_same_path_with_different_number_is_not_resent(self):
        self.schedule([row(), row(2, 動画='1.mp4')])
        publisher.main()
        self.assertEqual(self.mock.call_count, 1)

    def test_identical_bytes_under_different_names_is_not_resent(self):
        Path('1.mp4').write_bytes(b'same video')
        Path('2.mp4').write_bytes(b'same video')
        self.schedule([row(), row(2)])
        publisher.main()
        self.assertEqual(self.mock.call_count, 1)

    def test_uncertain_result_survives_rerun(self):
        self.schedule([row()])
        self.mock.side_effect = SystemExit('simulated timeout')
        with self.assertRaises(SystemExit):
            publisher.main()
        publisher.main()
        self.assertEqual(self.mock.call_count, 1)
        self.assertTrue(json.loads(Path('yotei.json').read_text())['予定'][0]['要確認'])

    def test_intent_save_failure_prevents_publish(self):
        self.schedule([row()])
        with patch.object(publisher, 'checkpoint', side_effect=RuntimeError('remote unavailable')):
            with self.assertRaises(SystemExit):
                publisher.main()
        self.mock.assert_not_called()

    def test_success_record_save_failure_never_resends(self):
        self.schedule([row()])
        calls = []
        def checkpoint(y):
            publisher.save(y)
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError('push response lost')
        with patch.object(publisher, 'checkpoint', side_effect=checkpoint):
            with self.assertRaises(SystemExit):
                publisher.main()
        publisher.main()
        self.assertEqual(self.mock.call_count, 1)

    def test_local_concurrent_run_does_not_publish(self):
        self.schedule([row()])
        with open('.instagram-publisher.lock', 'a+') as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(SystemExit):
                publisher.main()
        self.mock.assert_not_called()

    def test_future_item_is_not_published(self):
        self.schedule([row(日='2999-01-01')])
        publisher.main()
        self.mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
