import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("multi_plan", ROOT / "scripts/validate_plan.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class MultiArtworkTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / "examples/playful/multi-artwork-playful-plan.json").read_text())

    def check(self):
        return module.validate_plan(self.plan, ROOT)

    def test_comparison_example_and_legacy_examples_remain_valid(self):
        self.assertFalse(self.check()["errors"])
        for path in (ROOT / "examples").rglob("*plan.json"):
            plan = json.loads(path.read_text())
            self.assertFalse(module.validate_plan(plan, path.parent)["errors"], path.name)

    def test_duplicate_or_missing_work_identity_is_rejected(self):
        self.plan["artworks"].append(copy.deepcopy(self.plan["artworks"][0]))
        self.assertTrue(self.check()["errors"])
        self.plan["artworks"][0]["id"] = []
        self.assertTrue(self.check()["errors"])

    def test_each_image_asset_must_bind_its_own_work(self):
        self.plan["assets"][1]["artwork_id"] = "not-declared"
        self.assertTrue(self.check()["errors"])
        self.plan["assets"][1]["artwork_id"] = []
        self.assertTrue(self.check()["errors"])

    def test_comparison_requires_question_axes_and_mode(self):
        original = copy.deepcopy(self.plan["comparison"])
        for bad in (None, {}, {**original, "question": ""},
                    {**original, "axes": []}, {**original, "mode": []}):
            self.plan["comparison"] = bad
            self.assertTrue(self.check()["errors"])

    def test_multi_work_and_legacy_root_are_mutually_exclusive(self):
        self.plan["artwork"] = {"title": "legacy", "sources": []}
        self.assertTrue(self.check()["errors"])

    def test_pair_needs_declared_identity_labels_and_axis(self):
        shot = self.plan["shots"][0]
        shot.pop("labels")
        self.assertTrue(self.check()["errors"])
        shot["labels"] = {"xishan": "A"}
        self.assertTrue(self.check()["errors"])
        shot["labels"]["early-spring"] = "B"
        self.assertFalse(self.check()["errors"])
        shot.pop("comparison_axis")
        self.assertTrue(self.check()["errors"])

    def test_every_comparison_evidence_asset_must_be_original(self):
        self.plan["assets"][1]["kind"] = "ai-image"
        self.assertTrue(self.check()["errors"])

    def test_asset_ids_are_unambiguous_and_known(self):
        original = copy.deepcopy(self.plan["shots"][0])
        for refs in ([], [["bad"]], ["unknown"], ["xishan-original", "xishan-original"]):
            self.plan["shots"][0] = {**original, "asset_ids": refs}
            self.assertTrue(self.check()["errors"])
        self.plan["shots"][0] = {**original, "asset_id": "xishan-original"}
        self.assertTrue(self.check()["errors"])

    def test_work_sources_and_artist_are_individual(self):
        self.plan["artworks"][1]["sources"] = []
        self.assertTrue(self.check()["errors"])
        self.plan["artworks"][1]["artist"] = None
        self.assertTrue(self.check()["errors"])

    def test_editing_style_is_optional_and_independent_from_work_count(self):
        self.plan.pop("editing_style")
        self.assertFalse(self.check()["errors"])
        self.plan["editing_style"] = "contemplative"
        self.assertFalse(self.check()["errors"])
        self.plan["editing_style"] = "playful-art-history"
        self.assertFalse(self.check()["errors"])
        self.plan["editing_style"] = "theatre"
        self.assertFalse(self.check()["errors"])
        self.plan["editing_style"] = "not-a-style"
        self.assertTrue(self.check()["errors"])
        self.plan["editing_style"] = []
        self.assertTrue(self.check()["errors"])


if __name__ == "__main__":
    unittest.main()
