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

    def test_classic_plans_stay_on_ken_burns(self):
        for path in sorted((ROOT / "examples").glob("*-plan.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            result = MODULE.validate_plan(data, path.parent)
            self.assertEqual(result["errors"], [], path.name)
            if data.get("style", "ken-burns") == "ken-burns":
                self.assertEqual(result["style"], "ken-burns", path.name)
            else:
                self.assertEqual(result["style"], data["style"], path.name)
        self.plan["shots"][1]["ai_label"] = "generated"
        self.plan["shots"][1]["camera"] = "landscape-pov"
        self.plan["style"] = "ken-burns"
        result = self.validate()
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["style"], "ken-burns")
        self.plan["style"] = {"id": "ken-burns"}
        self.assertTrue(self.validate()["errors"])

    def test_evidence_dialogue_skeleton_and_guards(self):
        skeleton = json.loads((ROOT / "examples/evidence-dialogue-plan.json").read_text(encoding="utf-8"))
        result = MODULE.validate_plan(skeleton, ROOT)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["style"], "evidence-dialogue")
        self.assertTrue(result["warnings"])

        portrait = copy.deepcopy(skeleton)
        portrait["video"].update(width=1080, height=1920, orientation="portrait")
        self.assertEqual(MODULE.validate_plan(portrait, ROOT)["errors"], [])

        classic = copy.deepcopy(skeleton)
        classic["style"] = "ken-burns"
        classic["video"]["duration_seconds"] = 90
        classic["shots"][-1]["end"] = 90
        self.assertEqual(MODULE.validate_plan(classic, ROOT)["errors"], [])

        too_long = copy.deepcopy(skeleton)
        too_long["video"]["duration_seconds"] = 90
        too_long["shots"][-1]["end"] = 90
        self.assertTrue(MODULE.validate_plan(too_long, ROOT)["errors"])

        unlabeled = copy.deepcopy(skeleton)
        unlabeled["shots"][1]["ai_label"] = "AI"
        self.assertTrue(any("readable" in item for item in MODULE.validate_plan(unlabeled, ROOT)["errors"]))
        labeled = copy.deepcopy(skeleton)
        labeled["shots"][1]["ai_label"] = "AI 想象演绎"
        self.assertEqual(MODULE.validate_plan(labeled, ROOT)["errors"], [])

        cosplay = copy.deepcopy(skeleton)
        cosplay["shots"][1]["camera"] = "landscape-pov"
        self.assertTrue(any("first-person" in item for item in MODULE.validate_plan(cosplay, ROOT)["errors"]))

        other_engine = copy.deepcopy(skeleton)
        other_engine["assets"][2]["generator"] = "kling"
        self.assertTrue(any("seedance" in item for item in MODULE.validate_plan(other_engine, ROOT)["errors"]))

        second_painting = copy.deepcopy(skeleton)
        second_painting["assets"].append({"id": "other", "kind": "original"})
        second_painting["shots"][5]["asset_id"] = "other"
        self.assertTrue(any("one original" in item for item in MODULE.validate_plan(second_painting, ROOT)["errors"]))

        missing_idea = copy.deepcopy(skeleton)
        missing_idea.pop("idea")
        self.assertTrue(any("idea" in item for item in MODULE.validate_plan(missing_idea, ROOT)["errors"]))

        reordered = copy.deepcopy(skeleton)
        reordered["shots"][0]["start"], reordered["shots"][0]["end"] = 6, 12
        reordered["shots"][1]["start"], reordered["shots"][1]["end"] = 0, 6
        self.assertTrue(MODULE.validate_plan(reordered, ROOT)["errors"])


if __name__ == "__main__":
    unittest.main()
