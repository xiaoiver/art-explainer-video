#!/usr/bin/env python3
"""Read-only checks for a painting-video plan; Python 3.9+, optional ffprobe."""

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import subprocess
import sys


KINDS = {"original", "ai-image", "ai-video", "audio", "graphic"}
PURPOSES = {"analysis", "atmosphere", "title"}


def positive_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def aspect(width, height):
    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def inspect_media(path):
    """Probe the first visual stream; this does not decode or audition media."""
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if completed.returncode:
        raise ValueError("ffprobe could not read this file")
    media = json.loads(completed.stdout)
    streams = media.get("streams", [])
    if not streams:
        raise ValueError("no visual stream")
    stream = streams[0]
    result = {"width": stream["width"], "height": stream["height"]}
    for field in ("avg_frame_rate", "r_frame_rate"):
        try:
            rate = float(Fraction(stream.get(field, "0/1")))
            if rate > 0:
                result["fps"] = rate
                break
        except (ValueError, ZeroDivisionError):
            continue
    try:
        duration = float(media.get("format", {}).get("duration"))
        if math.isfinite(duration):
            result["duration_seconds"] = duration
    except (ValueError, TypeError):
        pass
    return result


def validate_plan(data, base_dir, check_files=False, probe=False):
    errors, warnings = [], []
    result = {"errors": errors, "warnings": warnings, "ratios": {}, "measurements": {}}
    if not isinstance(data, dict):
        errors.append("plan must be a JSON object")
        return result
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        errors.append("schema_version must be 1")
    artwork = data.get("artwork")
    if not isinstance(artwork, dict) or not isinstance(artwork.get("title"), str) or not artwork["title"].strip():
        errors.append("artwork.title is required")
    elif not isinstance(artwork.get("sources"), list) or not artwork["sources"]:
        warnings.append("artwork.sources has no references; verify provenance separately")

    sizes = {}
    for key in ("video", "cover"):
        if key == "cover" and key not in data:
            continue
        spec = data.get(key)
        if not isinstance(spec, dict):
            errors.append(f"{key} must be an object")
            continue
        if any(type(spec.get(n)) is not int or spec[n] <= 0 for n in ("width", "height")):
            errors.append(f"{key} width and height must be positive integers")
            continue
        sizes[key] = spec
        result["ratios"][key] = aspect(spec["width"], spec["height"])
    video = data.get("video", {})
    duration = video.get("duration_seconds") if isinstance(video, dict) else None
    fps = video.get("fps") if isinstance(video, dict) else None
    if not positive_number(duration):
        errors.append("video.duration_seconds must be finite and positive")
    if not positive_number(fps):
        errors.append("video.fps must be finite and positive")

    def local_file(value, label):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label} needs a local file path")
            return None
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = Path(base_dir) / path
        if not path.is_file():
            errors.append(f"{label} local file does not exist")
            return None
        return path

    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        errors.append("assets must be a nonempty array")
        assets = []
    by_id = {}
    for index, asset in enumerate(assets):
        label = f"assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{label} must be an object")
            continue
        identifier = asset.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append(f"{label}.id must be a nonempty string")
            continue
        if identifier in by_id:
            errors.append(f"duplicate asset id: {identifier}")
        by_id[identifier] = asset
        if not isinstance(asset.get("kind"), str) or asset["kind"] not in KINDS:
            errors.append(f"{label}.kind is unsupported")
        if check_files or probe:
            local_file(asset.get("path"), label)
        elif not asset.get("path"):
            warnings.append(f"{label} has no local path (planning only)")

    shots = data.get("shots")
    if not isinstance(shots, list) or not shots:
        errors.append("shots must be a nonempty array")
        shots = []
    intervals, shot_ids = [], set()
    for index, shot in enumerate(shots):
        label = f"shots[{index}]"
        if not isinstance(shot, dict):
            errors.append(f"{label} must be an object")
            continue
        identifier = shot.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append(f"{label}.id must be a nonempty string")
        elif identifier in shot_ids:
            errors.append(f"duplicate shot id: {identifier}")
        else:
            shot_ids.add(identifier)
        start, end = shot.get("start"), shot.get("end")
        if (type(start) not in (int, float) or not math.isfinite(start)
                or start < 0 or not positive_number(end) or end <= start):
            errors.append(f"{label} needs finite times with 0 <= start < end")
        else:
            intervals.append((start, end))
            if positive_number(duration) and end > duration + 1e-6:
                errors.append(f"{label} extends beyond video duration")
        asset_id = shot.get("asset_id")
        asset = by_id.get(asset_id) if isinstance(asset_id, str) else None
        if asset is None:
            errors.append(f"{label} references an unknown asset")
            continue
        purpose = shot.get("purpose")
        if not isinstance(purpose, str) or purpose not in PURPOSES:
            errors.append(f"{label}.purpose is unsupported")
        if purpose == "analysis" and asset.get("kind") != "original":
            errors.append(f"{label} analysis must reference original artwork")
        if asset.get("kind") == "audio":
            errors.append(f"{label} primary picture cannot be an audio asset")
        if asset.get("kind") in ("ai-image", "ai-video"):
            label_text = shot.get("ai_label")
            if not isinstance(label_text, str) or not label_text.strip():
                errors.append(f"{label} generated picture requires ai_label")
    covered_until = 0
    for start, end in sorted(intervals):
        if start > covered_until + 1e-6:
            errors.append(f"uncovered timeline interval: {covered_until:g}..{start:g}")
        covered_until = max(covered_until, end)
    if positive_number(duration) and covered_until < duration - 1e-6:
        errors.append(f"timeline ends at {covered_until:g}, before {duration:g}")

    deliverables = data.get("deliverables", {})
    if not isinstance(deliverables, dict):
        errors.append("deliverables must be an object")
        deliverables = {}
    for key in ("video", "cover"):
        if key not in deliverables and not (probe and (key == "video" or key in sizes)):
            continue
        if not (check_files or probe):
            continue
        path = local_file(deliverables.get(key), f"deliverables.{key}")
        if not probe or path is None:
            continue
        try:
            measured = inspect_media(path)
            result["measurements"][key] = measured
        except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
            errors.append(f"deliverables.{key}: probe failed ({type(exc).__name__})")
            continue
        if key in sizes:
            for dimension in ("width", "height"):
                if measured.get(dimension) != sizes[key][dimension]:
                    errors.append(f"deliverables.{key} {dimension} differs from plan")
        if key == "video":
            if positive_number(duration) and abs(measured.get("duration_seconds", -1) - duration) > 0.25:
                errors.append("deliverables.video duration differs from plan")
            if positive_number(fps) and abs(measured.get("fps", -1) - fps) > 0.02:
                errors.append("deliverables.video fps differs from plan")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--check-files", action="store_true", help="require local asset paths")
    parser.add_argument("--probe", action="store_true", help="also ffprobe final video and cover")
    args = parser.parse_args()
    try:
        data = json.loads(args.plan.read_text(encoding="utf-8"))
        report = validate_plan(data, args.plan.resolve().parent, args.check_files, args.probe)
    except (OSError, ValueError) as exc:
        report = {"errors": [f"cannot read plan: {type(exc).__name__}"], "warnings": []}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
