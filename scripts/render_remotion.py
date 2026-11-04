#!/usr/bin/env python3
"""Render project-authored compositions with an installed local Remotion CLI.

Python 3.9+ standard library. Does not install packages, generate assets or publish.
"""

import argparse
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

from validate_plan import validate_plan


def read_object(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return data


def frame_range(value):
    match = re.fullmatch(r"(\d+)-(\d+)", value)
    if not match or int(match[1]) > int(match[2]):
        raise argparse.ArgumentTypeError("use an inclusive frame range, e.g. 0-47")
    return int(match[1]), int(match[2])


def probe_output(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=30, check=True,
    )
    data = json.loads(result.stdout)
    stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not stream:
        raise ValueError("rendered output has no video/image stream")
    measured = {"width": stream["width"], "height": stream["height"]}
    if stream.get("avg_frame_rate") not in (None, "0/0"):
        measured["fps"] = float(Fraction(stream["avg_frame_rate"]))
    if data.get("format", {}).get("duration"):
        measured["duration_seconds"] = float(data["format"]["duration"])
    if stream.get("nb_frames", "").isdigit():
        measured["frames"] = int(stream["nb_frames"])
    return measured


def prepare(args):
    runtime = args.runtime.resolve()
    entry, props, public = args.entry.resolve(), args.props.resolve(), args.public_dir.resolve()
    output = args.output.resolve()
    if not runtime.is_dir() or not (runtime / "package.json").is_file():
        raise ValueError("runtime needs its own package.json; copy assets/remotion-runtime and run npm ci there")
    if not (runtime / "tsconfig.json").is_file():
        raise ValueError("runtime needs tsconfig.json; copy it from assets/remotion-runtime before launching the CLI")
    if not entry.is_relative_to(runtime):
        raise ValueError("entry must be inside runtime so its React/Remotion imports resolve locally")
    if not entry.is_file() or not props.is_file() or not public.is_dir():
        raise ValueError("entry, props and public-dir must exist")
    read_object(props)
    if output.is_relative_to(public):
        raise ValueError("output must be outside public-dir to avoid bundling generated outputs as assets")
    if output in (entry, props) or output == runtime / "package.json":
        raise ValueError("output cannot replace a source/configuration file")
    expected_suffix = ".png" if args.still_frame is not None else ".mp4"
    if output.suffix.lower() != expected_suffix:
        raise ValueError(f"this helper expects {expected_suffix} output")
    report = args.report.resolve() if args.report else output.with_suffix(".render.json")
    log = output.with_suffix(".renderer.log")
    protected = {entry, props, runtime / "package.json", runtime / "tsconfig.json",
                 runtime / "remotion.config.ts", output}
    if args.plan:
        protected.add(args.plan.resolve())
    if report in protected or report == log or report.is_relative_to(public) or log in protected:
        raise ValueError("report/log paths must be separate from sources, assets and rendered output")
    if not args.overwrite and any(f.exists() for f in (output, report, log)):
        raise ValueError("output or its report/log already exists; choose new paths or explicitly use --overwrite")
    if args.still_frame is not None and args.still_frame < 0:
        raise ValueError("still-frame must be nonnegative")
    if args.concurrency < 1 or not 0 <= args.crf <= 51:
        raise ValueError("concurrency must be positive; CRF must be 0..51")
    if not shutil.which("node") or not shutil.which("ffprobe"):
        raise ValueError("node and ffprobe must be on PATH; this helper does not install them")
    versions = {}
    for name in ("remotion", "@remotion/cli", "@remotion/renderer", "@remotion/bundler", "react", "react-dom"):
        package = runtime / "node_modules" / name / "package.json"
        if not package.is_file():
            raise ValueError(f"missing local {name}; run npm ci in runtime, without an external composer checkout")
        versions[name] = read_object(package)["version"]
    if len({v for name, v in versions.items() if "remotion" in name}) != 1:
        raise ValueError("installed Remotion package versions differ; install matching versions together")
    if versions["react"] != versions["react-dom"]:
        raise ValueError("installed react and react-dom versions differ")
    cli_package = runtime / "node_modules/@remotion/cli"
    cli = cli_package / read_object(cli_package / "package.json")["bin"]["remotion"]
    if not cli.is_file():
        raise ValueError("installed local Remotion CLI entry is missing")
    if args.browser_executable and not args.browser_executable.resolve().is_file():
        raise ValueError("browser-executable must be an existing executable file")
    plan = None
    if args.plan:
        plan = read_object(args.plan.resolve())
        inputs = deepcopy(plan)
        inputs.pop("deliverables", None)  # Outputs do not have to exist before rendering.
        checks = validate_plan(inputs, args.plan.resolve().parent, check_files=True)
        if checks["errors"]:
            raise ValueError("plan/input check failed: " + "; ".join(checks["errors"]))
    return runtime, entry, props, public, output, report, log, cli, versions, plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime", "entry", "props", "public-dir", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--composition", required=True)
    parser.add_argument("--plan", type=Path, help="optional art-video plan; check inputs before rendering")
    parser.add_argument("--report", type=Path)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--frames", type=frame_range)
    selection.add_argument("--still-frame", type=int)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--crf", type=int, default=18)
    parser.add_argument("--gl", help="optional Remotion GL backend, e.g. swangle on the tested Mac")
    parser.add_argument("--browser-executable", type=Path)
    parser.add_argument("--check", action="store_true", help="read-only preflight; do not launch the renderer")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        runtime, entry, props, public, output, report_path, log, cli, versions, plan = prepare(args)
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({"success": False, "error": str(error)}, ensure_ascii=False))
        return 2
    command = [shutil.which("node"), str(cli), "still" if args.still_frame is not None else "render",
               str(entry), args.composition, str(output), "--props=" + str(props), "--public-dir=" + str(public)]
    if args.still_frame is not None:
        command.append("--frame=" + str(args.still_frame))
    else:
        command += ["--codec=h264", "--crf=" + str(args.crf), "--concurrency=" + str(args.concurrency)]
        if args.frames:
            command.append("--frames=" + "-".join(map(str, args.frames)))
    if args.gl:
        command.append("--gl=" + args.gl)
    if args.browser_executable:
        command.append("--browser-executable=" + str(args.browser_executable.resolve()))
    report = {"success": False, "runtime": "remotion", "versions": versions,
              "output": str(output), "command": command, "log": str(log), "preflight_passed": True}
    if args.check:
        print(json.dumps({**report, "success": True, "check_only": True, "rendered": False},
                         ensure_ascii=False, indent=2))
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name("." + output.stem + "-" + uuid.uuid4().hex + output.suffix)
    command[5] = str(temporary)
    report["command"] = command
    code = 1
    try:
        with log.open("w", encoding="utf-8") as handle:
            rendered = subprocess.run(command, cwd=runtime, stdout=handle, stderr=subprocess.STDOUT, check=False)
        code = rendered.returncode
        if code:
            raise ValueError(f"renderer exited {code}; inspect renderer log")
        code = 1  # A renderer exit of zero alone does not establish a valid output.
        measured = probe_output(temporary)
        if args.still_frame is not None:
            measured = {key: measured[key] for key in ("width", "height")}
        if plan:
            expected = plan["video"]
            if any(measured[k] != expected[k] for k in ("width", "height")):
                raise ValueError("rendered dimensions differ from plan")
            if args.still_frame is None:
                duration = ((args.frames[1] - args.frames[0] + 1) / expected["fps"]
                            if args.frames else expected["duration_seconds"])
                if abs(measured.get("fps", 0) - expected["fps"]) > .02:
                    raise ValueError("rendered FPS differs from plan")
                if abs(measured.get("duration_seconds", 0) - duration) > .25:
                    raise ValueError("rendered duration differs from plan/range")
        temporary.replace(output)
        report.update(success=True, measurements=measured)
        code = 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        report["error"] = str(error)
    finally:
        if temporary.exists():
            temporary.unlink()
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
