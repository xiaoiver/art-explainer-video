import copy
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_sound", ROOT / "scripts/validate_sound.py")
sound = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sound)


class SoundPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.audio = self.base / "fixture.wav"
        with wave.open(str(self.audio), "wb") as writer:
            writer.setparams((2, 2, 48000, 0, "NONE", "not compressed"))
            samples = bytearray()
            for n in range(48000):
                # A local procedural test sound, with silence before and after.
                value = int(8192 * math.sin(2 * math.pi * 440 * n / 48000)) if 9600 <= n < 33600 else 0
                samples.extend(struct.pack("<hh", value, -value))
            writer.writeframes(samples)
        self.plan = {
            "schema_version": 1, "title": "Fixture", "status": "draft",
            "usage": "public-release", "duration_seconds": 2,
            "assets": [{
                "id": "tone", "title": "Local procedural test tone", "origin": "generated",
                "model": "local oscillator", "generation_record": "generated in this test, no service",
                "status": "selected", "path": "fixture.wav", "source_url": None,
                "author": "Test fixture author",
                "license": {"id": "self-created", "reviewed": True, "checked_on": "2026-11-02",
                            "usage_basis": "Procedural test fixture created locally, no third-party media"},
                "review": {"audition": "not-listened"},
            }],
            "cues": [{"id": "cue", "asset_id": "tone", "role": "event",
                      "intent": "Check energy position", "start": .25, "end": 1.25,
                      "source_in": 0, "source_out": 1, "gain_db": -5,
                      "fade_in": .02, "fade_out": .1, "loop": False}],
        }

    def validate(self, **kwargs):
        # Structural/rights tests remain usable without external media tools.
        with patch.object(sound, "probe_audio",
                          return_value={"duration_seconds": 1, "codec": "pcm_s16le"}):
            return sound.validate_sound(self.plan, self.base, **kwargs)

    def test_ready_checks_existing_media_hash_and_keeps_unauditioned_warning(self):
        result = self.validate(ready=True)
        self.assertFalse(result["errors"])
        self.assertEqual(result["media"]["tone"]["sha256"],
                         hashlib.sha256(self.audio.read_bytes()).hexdigest())
        self.assertFalse(result["audition_verified_by_script"])
        self.assertTrue(any("not auditioned" in x for x in result["warnings"]))

    def test_draft_keeps_unknown_candidate_but_ready_rejects_it(self):
        asset = self.plan["assets"][0]
        asset.update(path=None, status="candidate", license=None)
        self.assertFalse(self.validate()["errors"])
        self.assertTrue(self.validate()["warnings"])
        self.assertTrue(self.validate(ready=True)["errors"])

    def test_unknown_license_never_becomes_cc0(self):
        for value in (None, [], ["bad"], {}, {"id": "unknown", "reviewed": True}):
            with self.subTest(license=value):
                self.plan["assets"][0]["license"] = value
                self.assertTrue(self.validate(ready=True)["errors"])

    def cc_by(self, noncommercial=False):
        asset = self.plan["assets"][0]
        asset.update(origin="recorded", source_url="https://example.org/sounds/1")
        asset["license"] = {
            "id": "CC-BY-NC-4.0" if noncommercial else "CC-BY-4.0",
            "url": "https://creativecommons.org/licenses/by-nc/4.0/" if noncommercial
                   else "https://creativecommons.org/licenses/by/4.0/",
            "reviewed": True, "checked_on": "2026-11-02",
            "attribution": "Fixture by Test fixture author, source https://example.org/sounds/1",
        }

    def test_attribution_requires_author_source_and_complete_credit(self):
        self.cc_by()
        self.assertFalse(self.validate(ready=True)["errors"])
        self.plan["assets"][0]["license"].pop("attribution")
        self.assertTrue(self.validate(ready=True)["errors"])

    def test_nc_needs_explicit_noncommercial_usage(self):
        self.cc_by(noncommercial=True)
        self.assertTrue(self.validate(ready=True)["errors"])
        self.plan["usage"] = "noncommercial"
        self.assertFalse(self.validate(ready=True)["errors"])

    def test_generated_requires_generation_record_even_when_reused(self):
        self.plan["assets"][0].update(reused_from="episode-previous")
        self.plan["assets"][0].pop("generation_record")
        self.assertTrue(self.validate(ready=True)["errors"])

    def test_bad_refs_times_and_fades(self):
        original = copy.deepcopy(self.plan["cues"][0])
        for values in [
            {"asset_id": ["bad"]}, {"asset_id": "missing"}, {"start": -1},
            {"end": 3}, {"source_in": 1, "source_out": 0},
            {"source_out": float("nan")}, {"gain_db": float("inf")},
            {"fade_out": 1.1}, {"loop": True, "loop_crossfade": .5},
            {"loop": "yes"}, {"id": None},
        ]:
            with self.subTest(values=values):
                self.plan["cues"][0] = {**original, **values}
                self.assertTrue(self.validate()["errors"])

    def test_source_range_cannot_exceed_actual_media(self):
        self.plan["cues"][0].update(end=1.45, source_out=1.2)
        self.assertTrue(any("actual audio duration" in x
                            for x in self.validate(probe=True)["errors"]))

    def test_audio_layers_can_overlap_and_leave_gaps(self):
        self.plan["cues"].append({**self.plan["cues"][0], "id": "second", "role": "ambience"})
        self.assertFalse(self.validate(ready=True)["errors"])

    def test_rejected_asset_cannot_be_reintroduced(self):
        self.plan["assets"][0]["status"] = "rejected"
        self.assertTrue(self.validate()["errors"])

    def test_unused_candidates_do_not_need_local_media(self):
        candidate = copy.deepcopy(self.plan["assets"][0])
        candidate.update(id="unused", path="missing.wav", status="candidate", license=None)
        self.plan["assets"].append(candidate)
        self.assertFalse(self.validate(ready=True)["errors"])

    def test_urls_reject_credentials_and_signed_tokens(self):
        for url in ("https://user:secret@example.org/clip", "https://example.org/?token=secret",
                    "file:///tmp/test", "not-a-url"):
            with self.subTest(url=url):
                self.plan["assets"][0]["source_url"] = url
                self.assertTrue(self.validate()["errors"])

    def test_bad_roots_report_errors(self):
        for value in (None, [], 3, {"assets": None, "cues": None}):
            self.assertTrue(sound.validate_sound(value, self.base)["errors"])

    def test_public_draft_has_no_recordings_or_license_claims(self):
        example = json.loads((ROOT / "examples/contemplative/ruihe-sound-draft.json").read_text())
        self.assertFalse(sound.validate_sound(example, ROOT / "examples")["errors"])
        self.assertTrue(sound.validate_sound(example, ROOT / "examples", ready=True)["errors"])

    def cli(self, *args):
        plan = self.base / "plan.json"
        plan.write_text(json.dumps(self.plan))
        return subprocess.run([sys.executable, str(ROOT / "scripts/validate_sound.py"),
                               str(plan), *map(str, args)], capture_output=True, text=True)

    def test_export_never_overwrites_source_or_plan(self):
        before = self.audio.read_bytes()
        for flag in ("--report", "--cue-sheet", "--credits"):
            result = self.cli(flag, self.audio)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.audio.read_bytes(), before)
        result = self.cli("--report", self.base / "plan.json")
        self.assertNotEqual(result.returncode, 0)

    @unittest.skipUnless(shutil.which("ffprobe") and shutil.which("ffmpeg"), "requires ffmpeg/ffprobe")
    def test_actual_media_analyze_and_exports(self):
        report, sheet, credits = [self.base / n for n in ("report.json", "cues.csv", "credits.txt")]
        result = self.cli("--ready", "--analyze", "--report", report,
                          "--cue-sheet", sheet, "--credits", credits)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        data = json.loads(report.read_text())
        measurement = data["cue_measurements"]["cue"]
        # The opposite-phase stereo tone must not disappear in a mono downmix.
        self.assertAlmostEqual(measurement["source_excerpt_peak_dbfs"], -12.04, delta=.1)
        self.assertAlmostEqual(measurement["source_excerpt_rms_dbfs"], -18.06, delta=.1)
        self.assertAlmostEqual(measurement["first_energy_seconds"], .2, delta=.002)
        self.assertAlmostEqual(measurement["last_energy_seconds"], .7, delta=.002)
        self.assertIn("Test fixture author", credits.read_text())
        with sheet.open(encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(rows[0]["gain_db"], "-5")
        self.assertEqual(rows[0]["asset_id"], "tone")

    @unittest.skipUnless(shutil.which("ffprobe") and shutil.which("ffmpeg"), "requires ffmpeg/ffprobe")
    def test_silence_and_non_audio_download_fail(self):
        self.plan["cues"][0].update(source_out=.1, fade_out=.01)
        result = self.cli("--analyze")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("digital silence", result.stdout)
        self.audio.write_text("<html>not the requested audio</html>")
        result = self.cli("--probe")
        self.assertNotEqual(result.returncode, 0)

    @unittest.skipUnless(shutil.which("ffprobe"), "requires ffprobe")
    def test_failed_validation_exports_diagnostics_only(self):
        self.plan["assets"][0]["license"] = None
        report, sheet, credits = [self.base / n for n in ("bad.json", "bad.csv", "bad.txt")]
        result = self.cli("--credits", credits, "--cue-sheet", sheet, "--report", report)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(json.loads(report.read_text())["errors"])
        self.assertFalse(sheet.exists())
        self.assertFalse(credits.exists())


if __name__ == "__main__":
    unittest.main()
