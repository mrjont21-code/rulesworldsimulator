"""
tests/test_rule_library.py — Unit test cho rule_library.py (Global Rule
Library / Check G), theo §9 SPEC_GLOBAL_RULE_LIBRARY_v1_0.md.

Chạy: python3 -m unittest tests.test_rule_library -v  (từ thư mục repo1/)
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rule_library import evaluate_all, evaluate_rule, load_active_rules


class TestEvaluateRule(unittest.TestCase):
    def test_hit_when_all_terms_present_error(self):
        rule = {
            "rule_id": "RULE-MC-001",
            "rule_type": "forbidden_term_combo",
            "severity": "ERROR",
            "condition": {"terms": ["mc_female", "heavy armor"]},
            "message": "vi phạm",
            "suggestion": "sửa",
        }
        blueprint = {"character": "mc_female", "gear": "heavy armor set"}
        hit = evaluate_rule(rule, blueprint)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["rule_id"], "RULE-MC-001")
        self.assertEqual(hit["severity"], "ERROR")

    def test_none_when_missing_one_term(self):
        rule = {
            "rule_id": "RULE-MC-001",
            "rule_type": "forbidden_term_combo",
            "severity": "ERROR",
            "condition": {"terms": ["mc_female", "heavy armor"]},
        }
        blueprint = {"character": "mc_female", "gear": "light armor"}
        self.assertIsNone(evaluate_rule(rule, blueprint))

    def test_none_and_no_raise_for_unsupported_rule_type(self):
        rule = {
            "rule_id": "RULE-FUTURE-001",
            "rule_type": "field_condition",
            "severity": "ERROR",
            "condition": {},
        }
        blueprint = {"anything": "here"}
        self.assertIsNone(evaluate_rule(rule, blueprint))


class TestEvaluateAll(unittest.TestCase):
    def test_does_not_crash_on_malformed_rule(self):
        rules = [
            {"rule_id": "BAD-1", "rule_type": "forbidden_term_combo"},  # missing condition
            {
                "rule_id": "BAD-2",
                "rule_type": "forbidden_term_combo",
                "condition": {"terms": "not_a_list"},  # wrong type
            },
            {
                "rule_id": "GOOD-1",
                "rule_type": "forbidden_term_combo",
                "severity": "WARNING",
                "condition": {"terms": ["desert", "snow"]},
            },
        ]
        blueprint = {"biome": "desert with snow"}
        hits = evaluate_all(rules, blueprint)
        # GOOD-1 phải match (terms is a string, iterated as chars — nhưng
        # không được raise); ít nhất không crash toàn bộ evaluate_all.
        rule_ids = [h["rule_id"] for h in hits]
        self.assertIn("GOOD-1", rule_ids)

    def test_multiple_hits_returned(self):
        rules = [
            {
                "rule_id": "R1",
                "rule_type": "forbidden_term_combo",
                "severity": "ERROR",
                "condition": {"terms": ["a", "b"]},
            },
            {
                "rule_id": "R2",
                "rule_type": "forbidden_term_combo",
                "severity": "WARNING",
                "condition": {"terms": ["c"]},
            },
        ]
        blueprint = {"x": "a b c"}
        hits = evaluate_all(rules, blueprint)
        self.assertEqual({h["rule_id"] for h in hits}, {"R1", "R2"})


class _FailingCollection:
    def find(self, *_args, **_kwargs):
        raise RuntimeError("mongo query lỗi giả lập")


class _FailingDB:
    def __getitem__(self, _name):
        return _FailingCollection()


class TestLoadActiveRules(unittest.TestCase):
    def test_none_db_returns_empty_fail_open(self):
        self.assertEqual(load_active_rules(None), [])

    def test_failing_db_returns_empty_fail_open(self):
        self.assertEqual(load_active_rules(_FailingDB()), [])


if __name__ == "__main__":
    unittest.main()
