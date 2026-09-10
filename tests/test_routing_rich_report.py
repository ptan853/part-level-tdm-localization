import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core/scripts'))


class RichReportTests(unittest.TestCase):
    def test_query_and_head_views_have_explicit_different_averages(self):
        from report_attention_routing_rich import reduce_record
        a = np.arange(24, dtype=np.float32).reshape(2, 4, 3) / 100
        mask = np.array([[1, 0], [1, 0]])
        result = reduce_record(a, mask)
        np.testing.assert_allclose(result['queries'], a[:, [0, 2]].mean(0))
        np.testing.assert_allclose(result['heads'], a[:, [0, 2]].mean(1))
        np.testing.assert_allclose(result['mean'], a[:, [0, 2]].mean((0,1)))
        self.assertEqual(result['coordinates'], [[0,0], [1,0]])


if __name__ == '__main__':
    unittest.main()
