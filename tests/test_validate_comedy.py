import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.validate_comedy import validate_comedy
from scripts.validate_plan import validate_plan


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/american-gothic-comedy-plan.json"


class ComedyChecks(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def errors(self):
        return validate_comedy(self.plan, EXAMPLE.parent)["errors"]

    def test_sample_and_existing_plans_use_base_format(self):
        self.assertEqual(self.errors(), [])
        self.assertEqual(len(self.plan["performance"]["characters"]), 2)
        self.assertTrue(20 <= self.plan["video"]["duration_seconds"] <= 30)
        for path in sorted((ROOT / "examples").glob("*-plan.json")):
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_plan(data, path.parent)["errors"], [])

    def test_motives_and_painting_detail_are_required(self):
        for target, field in ((self.plan["performance"], "detail"),
                              (self.plan["performance"], "conflict"),
                              (self.plan["performance"]["characters"][0], "want")):
            original = target.pop(field)
            self.assertTrue(self.errors())
            target[field] = original

    def test_two_characters_must_act_not_only_narrate(self):
        for line in self.plan["performance"]["lines"]:
            line["framing"] = "off-screen"
        self.assertTrue(any("two characters must speak on screen" in e for e in self.errors()))

    def test_original_evidence_cannot_be_used_for_lip_sync(self):
        line = self.plan["performance"]["lines"][2]
        line["framing"] = "on-screen"
        self.assertTrue(any("not original evidence" in e for e in self.errors()))

    def test_fact_needs_source_date_and_original_evidence(self):
        fact = self.plan["performance"]["facts"][0]
        for field, bad in (("source_url", ""), ("source_url", "https://[broken"),
                           ("accessed_on", "2026-02-30"), ("accessed_on", "20261101"),
                           ("original_location", ""), ("evidence_shot_id", "s03")):
            with self.subTest(field=field, bad=bad):
                old = fact[field]
                fact[field] = bad
                self.assertTrue(self.errors())
                fact[field] = old

    def test_fact_line_must_resolve_and_use_fact_ids(self):
        line = self.plan["performance"]["lines"][2]
        for refs in ([], ["missing"], [[]]):
            line["fact_ids"] = refs
            self.assertTrue(self.errors())
        line["fact_ids"] = ["f-title"]
        extra = copy.deepcopy(self.plan["performance"]["facts"][0])
        extra["id"] = "unused"
        self.plan["performance"]["facts"].append(extra)
        self.assertTrue(any("not linked" in e for e in self.errors()))

    def test_dialogue_timing_speakers_and_shots(self):
        line = self.plan["performance"]["lines"][0]
        for field, bad in (("start", True), ("end", float("nan")), ("end", 8.1),
                           ("speaker", "unknown"), ("shot_id", {})):
            with self.subTest(field=field):
                old = line[field]
                line[field] = bad
                self.assertTrue(self.errors())
                line[field] = old
        overlap = copy.deepcopy(line)
        overlap["id"] = "overlap"
        self.plan["performance"]["lines"].append(overlap)
        self.assertTrue(any("overlaps" in e for e in self.errors()))

    def test_generated_performance_needs_readable_disclosure(self):
        self.plan["shots"][1]["ai_label"] = "AI"
        self.assertTrue(any("readable" in e for e in self.errors()))
        self.plan["shots"][1]["ai_label"] = "AI dramatization · fictional dialogue"
        self.assertEqual(self.errors(), [])
        self.plan["shots"][1]["purpose"] = "analysis"
        self.assertTrue(self.errors())

    def test_malformed_performance_reports_errors(self):
        for bad in (None, [], {}, {"characters": [None], "facts": [{}], "lines": [{}]}):
            self.plan["performance"] = bad
            self.assertTrue(self.errors())
        for bad in ([], None, {"video": None}):
            self.assertTrue(validate_comedy(bad, ROOT)["errors"])

    def test_cli_planning_and_missing_media_are_distinct(self):
        command = [sys.executable, str(ROOT / "scripts/validate_comedy.py"), str(EXAMPLE)]
        planned = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.assertEqual(json.loads(planned.stdout)["errors"], [])
        media = subprocess.run(command + ["--check-files"], capture_output=True, text=True, check=False)
        self.assertEqual(media.returncode, 1)
        self.assertTrue(json.loads(media.stdout)["errors"])


if __name__ == "__main__":
    unittest.main()
