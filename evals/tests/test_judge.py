import unittest
from evals.judge import validate_judgment


class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.result = {"judgments": [{"criterion": "c1", "pass": True, "evidence": "Turn 1 states the null amount is unknown."}]}
        self.events = [{"type": "turn.completed"}]

    def test_valid_binary_label_with_evidence(self):
        self.assertEqual(validate_judgment(self.result, self.events, {"c1"}), self.result["judgments"])

    def test_missing_and_duplicate_criteria_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_judgment(self.result, self.events, {"c1", "c2"})
        self.result["judgments"] *= 2
        with self.assertRaises(ValueError):
            validate_judgment(self.result, self.events, {"c1"})

    def test_tool_use_cannot_contaminate_judge(self):
        for typ in ("command_execution", "mcp_tool_call", "web_search"):
            with self.subTest(typ=typ), self.assertRaises(ValueError):
                validate_judgment(self.result, self.events + [{"type": "item.completed", "item": {"type": typ}}], {"c1"})

    def test_no_completed_turn_rejected_even_if_json_looks_valid(self):
        with self.assertRaises(ValueError):
            validate_judgment(self.result, [], {"c1"})

    def test_nonbinary_or_unsupported_pass_rejected(self):
        for value in (1, "yes"):
            self.result["judgments"][0]["pass"] = value
            with self.assertRaises(ValueError):
                validate_judgment(self.result, self.events, {"c1"})

    def test_null_is_pending_and_empty_evidence_cannot_support_pass(self):
        self.result["judgments"][0].update({"pass": None, "evidence": ""})
        validate_judgment(self.result, self.events, {"c1"})
        self.result["judgments"][0]["pass"] = True
        with self.assertRaises(ValueError):
            validate_judgment(self.result, self.events, {"c1"})


if __name__ == "__main__":
    unittest.main()
