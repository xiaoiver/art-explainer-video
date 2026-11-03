import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_plan", ROOT / "scripts/validate_plan.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PlanChecks(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / "examples/xishan-plan.json").read_text(encoding="utf-8"))

    def validate(self, plan=None, **kwargs):
        return MODULE.validate_plan(self.plan if plan is None else plan, ROOT, **kwargs)

    def test_planning_example_and_independent_ratios(self):
        result = self.validate()
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["ratios"], {"video": "16:9", "cover": "4:3"})
        self.assertTrue(result["warnings"])

    def test_generated_picture_cannot_replace_evidence(self):
        self.plan["shots"][1]["purpose"] = "analysis"
        self.assertTrue(self.validate()["errors"])

    def test_orientation_and_cover_remain_independent(self):
        self.plan["video"].update(width=1080, height=1920, orientation="portrait")
        result = self.validate()
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["ratios"], {"video": "9:16", "cover": "4:3"})
        self.plan["video"]["orientation"] = "landscape"
        self.assertTrue(self.validate()["errors"])
        for bad in ([], None, "vertical"):
            self.plan["video"]["orientation"] = bad
            self.assertTrue(self.validate()["errors"])

    def test_portrait_plan_cannot_pass_with_landscape_media(self):
        self.plan["video"].update(width=1080, height=1920, orientation="portrait")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "asset.bin").write_bytes(b"fixture")
            for asset in self.plan["assets"]:
                asset["path"] = "asset.bin"
            self.plan["deliverables"] = {"video": "asset.bin", "cover": "asset.bin"}
            media = [{"width": 1920, "height": 1080, "fps": 24, "duration_seconds": 90},
                     {"width": 2304, "height": 1728}]
            with patch.object(MODULE, "inspect_media", side_effect=media):
                result = MODULE.validate_plan(self.plan, base, probe=True)
            self.assertTrue(any("width differs" in item for item in result["errors"]))

    def test_generated_picture_needs_disclosure(self):
        self.plan["shots"][1].pop("ai_label")
        self.assertTrue(self.validate()["errors"])

    def test_gaps_and_overruns_are_rejected(self):
        self.plan["shots"][1]["start"] += 1
        self.assertTrue(self.validate()["errors"])
        self.plan["shots"][1]["start"] -= 1
        self.plan["shots"][-1]["end"] += 1
        self.assertTrue(self.validate()["errors"])

    def test_dissolve_overlap_is_accepted(self):
        self.plan["shots"][1]["start"] -= 0.25
        self.assertEqual(self.validate()["errors"], [])

    def test_unknown_asset_and_duplicates_are_rejected(self):
        self.plan["shots"][0]["asset_id"] = "missing"
        self.assertTrue(self.validate()["errors"])
        self.plan["assets"].append(copy.deepcopy(self.plan["assets"][0]))
        self.assertTrue(self.validate()["errors"])

    def test_nonfinite_and_malformed_input_returns_errors(self):
        for bad in ([], {"schema_version": 1}, {"video": None}):
            with self.subTest(bad=bad):
                self.assertTrue(self.validate(bad)["errors"])
        for field in ("fps", "duration_seconds"):
            for value in (float("nan"), float("inf"), True, -1):
                with self.subTest(field=field, value=value):
                    altered = copy.deepcopy(self.plan)
                    altered["video"][field] = value
                    self.assertTrue(self.validate(altered)["errors"])

    def test_missing_files_fail_only_when_requested(self):
        self.assertEqual(self.validate()["errors"], [])
        self.assertTrue(self.validate(check_files=True)["errors"])

    def test_malformed_enum_fields_report_errors(self):
        self.plan["assets"][0]["kind"] = []
        self.plan["shots"][0]["purpose"] = {}
        self.assertTrue(self.validate()["errors"])

    def test_relative_paths_and_actual_media_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "asset.bin").write_bytes(b"fixture")
            for asset in self.plan["assets"]:
                asset["path"] = "asset.bin"
            self.plan["deliverables"] = {"video": "asset.bin", "cover": "asset.bin"}
            correct = [
                {"width": 1920, "height": 1080, "fps": 24, "duration_seconds": 90.047},
                {"width": 2304, "height": 1728},
            ]
            with patch.object(MODULE, "inspect_media", side_effect=correct):
                result = MODULE.validate_plan(self.plan, base, probe=True)
            self.assertEqual(result["errors"], [])
            wrong = [correct[0], {"width": 2304, "height": 1296}]
            with patch.object(MODULE, "inspect_media", side_effect=wrong):
                result = MODULE.validate_plan(self.plan, base, probe=True)
            self.assertTrue(result["errors"])

    def test_probe_requires_deliverables(self):
        result = self.validate(probe=True)
        self.assertTrue(any("deliverables.video" in error for error in result["errors"]))
        self.assertTrue(any("deliverables.cover" in error for error in result["errors"]))


class EditorialOverlayChecks(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / "examples/editorial-annotation-plan.json").read_text(encoding="utf-8"))

    def validate(self):
        return MODULE.validate_plan(self.plan, ROOT)

    def test_skeleton_passes_and_classic_plans_stay_untouched(self):
        result = self.validate()
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["ratios"]["video"], "9:16")
        classic = json.loads((ROOT / "examples/xishan-plan.json").read_text(encoding="utf-8"))
        playful = json.loads((ROOT / "examples/multi-artwork-playful-plan.json").read_text(encoding="utf-8"))
        self.assertEqual(MODULE.validate_plan(classic, ROOT)["errors"], [])
        self.assertEqual(MODULE.validate_plan(playful, ROOT)["errors"], [])

    def test_desk_cannot_hold_the_painting(self):
        shot = self.plan["shots"][1]
        shot["purpose"] = "analysis"
        shot["asset_id"] = "painting"
        errors = self.validate()["errors"]
        self.assertTrue(any("evidence desk" in item for item in errors))
        shot["purpose"] = "context"
        shot["asset_id"] = "catalogue-scan"
        shot["evidence_desk"]["subject"] = self.plan["artwork"]["title"]
        self.assertTrue(any("subject" in item for item in self.validate()["errors"]))
        shot["evidence_desk"]["subject"] = "馆藏说明摘句"
        shot["evidence_desk"]["not_painting"] = False
        self.assertTrue(any("not_painting" in item for item in self.validate()["errors"]))

    def test_citations_stay_off_generated_shots_and_keep_their_clock(self):
        self.plan["shots"][3]["annotations"] = [{
            "id": "fake", "kind": "underline", "role": "year", "text": "北宋",
            "source": "https://theme.npm.edu.tw/selection/Article.aspx?sNo=04000959",
            "start": 23, "end": 25,
        }]
        self.assertTrue(any("generated" in item for item in self.validate()["errors"]))
        self.plan["shots"][3].pop("annotations")
        note = self.plan["shots"][0]["annotations"][0]
        note.pop("source")
        self.assertTrue(any("source" in item for item in self.validate()["errors"]))
        note["source"] = "https://theme.npm.edu.tw/selection/Article.aspx?sNo=04000959"
        note["start"] = 1.5
        self.assertTrue(any("spoken word" in item for item in self.validate()["errors"]))

    def test_timing_rules_reject_fade_tear_and_a_red_line_into_atmosphere(self):
        timing = self.plan["shots"][0]["editorial_timing"]
        timing["entrance"] = "fade"
        self.assertTrue(any("spring" in item for item in self.validate()["errors"]))
        timing["entrance"] = "spring"
        timing["cut"] = "tear-paper"
        self.assertTrue(any("hard cut" in item for item in self.validate()["errors"]))
        timing["cut"] = "hard"
        timing["elements_fps"] = 24
        self.assertTrue(any("elements_fps" in item for item in self.validate()["errors"]))
        timing["elements_fps"] = 12
        self.plan["shots"][2]["editorial_timing"]["follow_red_line"] = True
        self.assertTrue(any("follow_red_line" in item for item in self.validate()["errors"]))

    def test_context_and_music_duck_keep_their_types(self):
        self.plan["shots"][1].pop("evidence_desk")
        self.assertTrue(any("context requires" in item for item in self.validate()["errors"]))
        self.plan["shots"][0]["music_duck"] = "yes"
        self.assertTrue(any("music_duck" in item for item in self.validate()["errors"]))


if __name__ == "__main__":
    unittest.main()
