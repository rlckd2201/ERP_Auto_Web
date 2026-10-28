import unittest

from web_v1.tools.approval_backtest import classify, historical_anchor, manual_events, summary, truth_numbers


class BacktestScoringTests(unittest.TestCase):
    def test_wrong_auto_link_is_not_counted_as_recovered(self):
        result = {"status": "matched", "selected": {"doc_no": "wrong"},
                  "candidates": [{"doc_no": "right"}]}
        self.assertEqual(classify(result, ["right"]), "auto_wrong")

    def test_correct_review_is_distinct_from_automatic(self):
        self.assertEqual(classify({"status": "review", "candidates": [{"doc_no": "right"}]}, ["right"]),
                         "review_correct_candidate")

    def test_errors_and_misses_remain_in_denominator(self):
        counts = summary([{"classification": label} for label in
                          ("auto_correct", "review_correct_candidate", "auto_wrong", "not_recovered", "error")])
        self.assertEqual(counts["n"], 5)
        self.assertEqual(counts["auto_correct_percent"], 20.0)
        self.assertEqual(counts["recovered_percent"], 40.0)

    def test_anchor_uses_first_actual_attempt_not_final_processed_date(self):
        record = {"invoice": {"processed_at": "2026-06-30"}, "logs": [
            {"created_at": "2026-06-09 10:00:00", "message": "품의결재본 교체: 1건"},
            {"created_at": "2026-06-01 09:00:00", "message": "품의결재본 백그라운드 자동 확보 시작"}]}
        self.assertEqual(historical_anchor(record)[0], "2026-06-01")

    def test_cohort_requires_explicit_upload_log(self):
        record = {"logs": [{"created_at": "2026-06-01", "message": "컴퓨존 견적서 자동첨부 완료"}]}
        self.assertFalse(manual_events(record))
        with self.assertRaises(ValueError):
            historical_anchor(record)

    def test_related_document_is_not_ground_truth(self):
        record = {"invoice": {"id": 1}, "files": [{"doc_nos": ["header", "related"]}]}
        self.assertEqual(truth_numbers(record, {}), ["header"])

    def test_scan_requires_independently_verified_override(self):
        record = {"invoice": {"id": 1}, "files": [{"doc_nos": []}]}
        with self.assertRaises(ValueError):
            truth_numbers(record, {})
        self.assertEqual(truth_numbers(record, {"1": {"doc_nos": ["visual"]}}), ["visual"])


if __name__ == "__main__":
    unittest.main()
