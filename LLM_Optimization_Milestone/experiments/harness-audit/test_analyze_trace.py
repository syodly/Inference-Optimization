"""Hand-authored correctness checks; these events are not performance evidence."""
import unittest
from analyze_trace import analyze


def event(kind, at, **fields):
    return {"run_id": "check", "policy": "native", "event": kind, "ts_ms": at, **fields}


class AuditTests(unittest.TestCase):
    def report(self, rows):
        return analyze(rows)["reports"][0]

    def test_arrival_offset_messages_and_missing_usage(self):
        report = self.report([
            event("task_start", 7, task_id="B"),
            event("message_accepted", 8, message_id="m1"),
            event("message_accepted", 9, message_id="m2"),
            event("message_accepted", 10, message_id="pending"),
            event("message_consumed", 11, message_id="m1", request_id="r1"),
            event("message_consumed", 11, message_id="m2", request_id="r1"),
            event("llm_end", 12, request_id="r1", actor="parent", input_tokens=100, cached_tokens=80),
            event("llm_end", 13, request_id="r2", actor="child", input_tokens=20, cached_tokens=None),
            event("task_end", 15, task_id="B", success=True),
        ])
        self.assertEqual(report["tasks"][0]["elapsed_ms"], 8)
        self.assertEqual(report["usage"]["input_tokens"], 120)
        self.assertIsNone(report["usage"]["cached_tokens"])
        self.assertEqual(report["parent_llm_requests"], 1)
        self.assertEqual(report["distinct_requests_consuming_new_messages"], 1)
        self.assertEqual(report["unconsumed_message_ids"], ["pending"])
        self.assertEqual(report["message_first_consumption"]["m1"]["wait_ms"], 3)

    def test_residency_is_integrated_and_open_work_is_censored(self):
        report = self.report([
            event("task_start", 0, task_id="unfinished"),
            event("activation_reserved", 0, activation_id="a"),
            event("activation_state", 2, activation_id="a", state="running"),
            event("activation_state", 5, activation_id="a", state="wait_children"),
            event("activation_reserved", 7, activation_id="b"),
            event("activation_released", 10, activation_id="a"),
            event("activation_rejected", 12, reason="ACTIVATION_LIMIT_REACHED"),
        ])
        self.assertEqual(report["observed_slot_ms_by_state"], {"materializing": 7, "running": 3, "wait_children": 5})
        self.assertEqual(report["unreleased_activation_ids"], ["b"])
        self.assertEqual(report["peak_observed_activation_slots"], 2)
        self.assertIsNone(report["tasks"][0]["elapsed_ms"])
        self.assertFalse(report["tasks"][0]["completed"])

    def test_duplicate_and_impossible_measurements_fail(self):
        bad_cases = [
            [event("llm_end", 1, request_id="r", actor="parent", input_tokens=5, cached_tokens=6)],
            [event("activation_reserved", 0, activation_id="a"), event("activation_reserved", 1, activation_id="a")],
            [event("message_consumed", 1, message_id="missing", request_id="r")],
            [event("task_end", 1, task_id="never-started")],
            [event("task_start", 0, task_id="t"), event("task_start", 1, task_id="t")],
        ]
        for rows in bad_cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                analyze(rows)


if __name__ == "__main__":
    unittest.main()
