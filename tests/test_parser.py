"""parse_findings must distinguish a genuine empty result from a malformed one."""

import unittest

from _support import rt


class StrictParserTest(unittest.TestCase):
    def test_empty_array_is_a_valid_empty_result(self):
        self.assertEqual(rt.parse_findings("[]"), [])

    def test_valid_findings_are_normalized(self):
        out = rt.parse_findings('[{"rule": "Adverbs", "quote": "fairly"}]')
        self.assertEqual(out, [{"rule": "Adverbs", "text": "fairly", "index": None, "severity": None}])

    def test_code_fence_and_surrounding_prose_are_tolerated(self):
        out = rt.parse_findings('Here you go:\n```json\n[{"rule": "r", "quote": "q"}]\n```')
        self.assertEqual(len(out), 1)

    def test_malformed_elements_reject_the_whole_response(self):
        for bad in ('[{}]', '[42]', '["bad response"]', '[{"quote": "q"}]',
                    '[{"rule": "r"}]', '[{"rule": "", "quote": "q"}]',
                    '[{"rule": "r", "quote": "   "}]', '[{"rule": 5, "quote": "q"}]',
                    '[{"rule": "r", "quote": "q"}, null]'):
            with self.subTest(bad=bad):
                self.assertIsNone(rt.parse_findings(bad))

    def test_non_array_or_invalid_json_is_unparseable(self):
        for bad in ('{"rule": "r", "quote": "q"}', "no array here", "[{\"rule\": \"r\", \"quote\": ]"):
            with self.subTest(bad=bad):
                self.assertIsNone(rt.parse_findings(bad))


if __name__ == "__main__":
    unittest.main()
