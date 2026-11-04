"""Failure and preflight behavior of the standalone renderer; no network/browser."""

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import render_remotion as render


class StandaloneRenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = self.root / "render"
        self.runtime.mkdir()
        (self.runtime / "package.json").write_text('{}')
        (self.runtime / "tsconfig.json").write_text('{}')
        for name in ("remotion", "@remotion/cli", "@remotion/renderer", "@remotion/bundler", "react", "react-dom"):
            package = self.runtime / "node_modules" / name
            package.mkdir(parents=True)
            data = {"version": "4.0.539" if "remotion" in name else "18.3.1"}
            if name == "@remotion/cli":
                data["bin"] = {"remotion": "remotion-cli.js"}
                (package / "remotion-cli.js").write_text('// fixture, never launched')
            (package / "package.json").write_text(json.dumps(data))
        self.entry = self.runtime / "index.tsx"
        self.entry.write_text('// fixture')
        self.props = self.root / "props.json"
        self.props.write_text('{"totalFrames":48}')
        self.public = self.root / "assets"
        self.public.mkdir()
        (self.public / "source.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        self.output = self.root / "out/film.mp4"
        self.args = ["--runtime", str(self.runtime), "--entry", str(self.entry),
                     "--composition", "Film", "--props", str(self.props),
                     "--public-dir", str(self.public), "--output", str(self.output)]
        self.bin_patch = patch.object(render.shutil, "which", side_effect=lambda x: "/fixture/bin/" + x)
        self.bin_patch.start()
        self.addCleanup(self.bin_patch.stop)

    def run_main(self, extra=()):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = render.main(self.args + list(extra))
        return code, json.loads(stdout.getvalue())

    def test_check_never_launches_or_writes_outputs(self):
        with patch.object(render.subprocess, "run") as process:
            code, report = self.run_main(["--check"])
        self.assertEqual(code, 0)
        self.assertTrue(report["check_only"])
        self.assertFalse(report["rendered"])
        process.assert_not_called()
        self.assertFalse(self.output.parent.exists())

    def test_missing_or_mixed_runtime_does_not_install_anything(self):
        package = self.runtime / "node_modules/@remotion/renderer/package.json"
        for content in ('{"version":"4.0.1"}', None):
            if content:
                package.write_text(content)
            else:
                package.unlink()
            with patch.object(render.subprocess, "run") as process:
                code, report = self.run_main(["--check"])
            self.assertEqual(code, 2)
            self.assertFalse(report["success"])
            process.assert_not_called()

    def test_missing_tsconfig_fails_before_a_browser_is_launched(self):
        (self.runtime / "tsconfig.json").unlink()
        with patch.object(render.subprocess, "run") as process:
            code, report = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("tsconfig", report["error"])
        process.assert_not_called()

    def test_invalid_props_and_existing_output_are_rejected(self):
        self.props.write_text('[]')
        self.assertEqual(self.run_main(["--check"])[0], 2)
        self.props.write_text('{}')
        self.output.parent.mkdir()
        self.output.write_bytes(b"old movie")
        self.assertEqual(self.run_main()[0], 2)
        self.assertEqual(self.output.read_bytes(), b"old movie")

    def test_renderer_failure_keeps_old_video_and_reports_failure(self):
        self.output.parent.mkdir()
        self.output.write_bytes(b"old movie")

        def fail(command, **kwargs):
            Path(command[5]).write_bytes(b"unfinished")
            return subprocess.CompletedProcess(command, 17)

        with patch.object(render.subprocess, "run", side_effect=fail):
            code, report = self.run_main(["--overwrite"])
        self.assertEqual(code, 17)
        self.assertFalse(report["success"])
        self.assertEqual(self.output.read_bytes(), b"old movie")
        self.assertFalse(list(self.output.parent.glob(".film-*.mp4")))
        self.assertFalse(json.loads(self.output.with_suffix('.render.json').read_text())["success"])

    def test_zero_exit_with_invalid_media_is_not_success(self):
        def partial(command, **kwargs):
            Path(command[5]).write_bytes(b"invalid media")
            return subprocess.CompletedProcess(command, 0)

        with patch.object(render.subprocess, "run", side_effect=partial), \
                patch.object(render, "probe_output", side_effect=ValueError("no video stream")):
            code, report = self.run_main()
        self.assertEqual(code, 1)
        self.assertFalse(report["success"])
        self.assertFalse(self.output.exists())

    def test_plan_checks_inputs_before_render_and_output_dimensions_after(self):
        plan = self.root / "project.json"
        data = {"schema_version": 1, "artwork": {"title": "check", "sources": ["https://example.org/work"]},
                "video": {"width": 320, "height": 180, "fps": 24, "duration_seconds": 2},
                "assets": [{"id": "image", "kind": "graphic", "path": "assets/source.svg"}],
                "shots": [{"id": "s1", "start": 0, "end": 2, "asset_id": "image", "purpose": "title"}],
                "deliverables": {"video": "out/not-generated-yet.mp4"}}
        plan.write_text(json.dumps(data))
        self.assertEqual(self.run_main(["--plan", str(plan), "--check"])[0], 0)

        def rendered(command, **kwargs):
            Path(command[5]).write_bytes(b"fake output")
            return subprocess.CompletedProcess(command, 0)

        with patch.object(render.subprocess, "run", side_effect=rendered), \
                patch.object(render, "probe_output", return_value={"width": 640, "height": 360, "fps": 24, "duration_seconds": 2}):
            code, report = self.run_main(["--plan", str(plan)])
        self.assertEqual(code, 1)
        self.assertIn("dimensions", report["error"])
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
