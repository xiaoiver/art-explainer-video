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
REGISTRY_PATH = Path(__file__).resolve().parents[1] / "references" / "style-registry.json"


def load_style_registry():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def normalize_token(value):
    return "".join(str(value).split()).casefold()


def finite_interval(shot):
    if not isinstance(shot, dict):
        return None
    start, end = shot.get("start"), shot.get("end")
    if (type(start) not in (int, float) or type(end) not in (int, float)
            or not math.isfinite(start) or not math.isfinite(end)
            or start < 0 or end <= start):
        return None
    return start, end


def union_seconds(intervals):
    if not intervals:
        return 0
    ordered = sorted(intervals)
    total = 0
    start, end = ordered[0]
    for nxt, stop in ordered[1:]:
        if nxt > end:
            total += end - start
            start, end = nxt, stop
        else:
            end = max(end, stop)
    return total + end - start


def resolve_style(data, errors, result):
    """Missing style stays on classic Ken Burns. Only a registered id adds rules."""
    try:
        registry = load_style_registry()
    except (OSError, ValueError) as exc:
        errors.append(f"style registry is unreadable ({type(exc).__name__})")
        return None, None
    styles = registry.get("styles") if isinstance(registry, dict) else None
    default = registry.get("default") if isinstance(registry, dict) else None
    if not isinstance(styles, dict) or not isinstance(default, str) or default not in styles:
        errors.append("style registry is invalid")
        return None, None
    if "style" not in data:
        result["style"] = default
        return default, styles[default]
    style_id = data.get("style")
    if not isinstance(style_id, str) or style_id not in styles:
        errors.append("style must be a registered style id")
        return None, None
    result["style"] = style_id
    return style_id, styles[style_id]


def validate_evidence_dialogue(data, shots, by_id, errors, warnings, spec):
    duration = data.get("video", {}).get("duration_seconds") if isinstance(data.get("video"), dict) else None
    window = spec.get("duration_seconds") if isinstance(spec.get("duration_seconds"), dict) else {}
    low, high = window.get("min"), window.get("max")
    if positive_number(duration) and (not positive_number(low) or not positive_number(high)
                                       or duration < low or duration > high):
        errors.append("evidence-dialogue duration must stay within the registered window around 60 seconds")
    idea = data.get("idea")
    if not isinstance(idea, str) or not idea.strip():
        errors.append("evidence-dialogue requires idea")
    elif len(idea.strip()) > 80:
        warnings.append("evidence-dialogue idea is longer than one short sentence")

    labels = spec.get("readable_ai_labels")
    readable = {normalize_token(item) for item in labels} if isinstance(labels, list) else set()
    forbidden = set(spec.get("cameras_forbidden") or [])
    beat_cameras = spec.get("beat_cameras") if isinstance(spec.get("beat_cameras"), dict) else {}
    beat_order = spec.get("beat_order") if isinstance(spec.get("beat_order"), list) else []
    ready = []
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            continue
        label = f"shots[{index}]"
        asset = by_id.get(shot.get("asset_id")) if isinstance(shot.get("asset_id"), str) else None
        kind = asset.get("kind") if isinstance(asset, dict) else None
        if kind in ("ai-image", "ai-video"):
            label_text = shot.get("ai_label")
            if isinstance(label_text, str) and label_text.strip() and normalize_token(label_text) not in readable:
                errors.append(f"{label} ai_label must be a readable on-screen disclosure")
        camera = shot.get("camera")
        if isinstance(camera, str) and camera in forbidden:
            errors.append(f"{label} forbids a landscape first-person viewpoint")
        beat = shot.get("beat")
        if not isinstance(beat, str) or beat not in beat_cameras:
            errors.append(f"{label} beat is not registered for evidence-dialogue")
            continue
        if finite_interval(shot) is None:
            continue
        allowed = beat_cameras.get(beat) or []
        if beat == "motion":
            if not isinstance(camera, str) or camera not in allowed:
                if not (isinstance(camera, str) and camera in forbidden):
                    errors.append(f"{label} motion camera must stay on the picture plane")
        elif camera is not None and camera not in allowed and camera not in forbidden:
            errors.append(f"{label} camera is not allowed for this beat")
        ready.append(shot)

    for asset_id, asset in by_id.items():
        if not isinstance(asset, dict) or asset.get("kind") != "ai-video":
            continue
        generator = normalize_token(asset.get("generator", ""))
        if not generator.startswith("seedance"):
            errors.append(f"asset {asset_id} generator must be seedance")

    if not beat_order:
        errors.append("style registry is missing evidence-dialogue beat order")
        return
    first_start = {}
    for beat in beat_order:
        starts = [shot["start"] for shot in ready if shot.get("beat") == beat]
        if not starts:
            errors.append(f"evidence-dialogue requires beat {beat}")
        else:
            first_start[beat] = min(starts)
    if len(first_start) == len(beat_order):
        for previous, nxt in zip(beat_order, beat_order[1:]):
            if first_start[nxt] <= first_start[previous]:
                errors.append("evidence-dialogue beats must run open-still, motion, scale, evidence, return-still")
                break
    order_index = {beat: index for index, beat in enumerate(beat_order)}
    last_index = -1
    for shot in sorted(ready, key=lambda item: (item["start"], order_index.get(item.get("beat"), 99))):
        index = order_index.get(shot.get("beat"), 99)
        if index < last_index:
            errors.append("evidence-dialogue beats must stay in open-still, motion, scale, evidence, return-still order")
            break
        last_index = index

    originals = set()
    evidence_count = 0
    for shot in ready:
        beat = shot.get("beat")
        asset = by_id.get(shot.get("asset_id"))
        kind = asset.get("kind") if isinstance(asset, dict) else None
        purpose = shot.get("purpose")
        if beat == "motion":
            if kind != "ai-video" or purpose != "atmosphere":
                errors.append(f"shot {shot.get('id', '?')} motion must be seedance atmosphere")
        elif beat in ("open-still", "return-still", "scale", "evidence"):
            if kind != "original":
                errors.append(f"shot {shot.get('id', '?')} {beat} must use the original painting")
            else:
                originals.add(shot.get("asset_id"))
            if beat in ("scale", "evidence") and purpose != "analysis":
                errors.append(f"shot {shot.get('id', '?')} {beat} must be analysis")
            if beat in ("open-still", "return-still") and purpose not in ("title", "analysis"):
                errors.append(f"shot {shot.get('id', '?')} {beat} purpose is unsupported")
        if beat == "evidence":
            evidence_count += 1
    if len(originals) > 1:
        errors.append("evidence-dialogue stays on one original painting")
    minimum = spec.get("evidence_min_shots")
    if type(minimum) is int and evidence_count < minimum:
        errors.append("evidence-dialogue needs two original evidence shots")

    def span(beat):
        selected = [shot for shot in ready if shot.get("beat") == beat]
        if not selected:
            return 0
        return max(shot["end"] for shot in selected) - min(shot["start"] for shot in selected)

    still_min = spec.get("still_seconds_min")
    if positive_number(still_min):
        for beat in ("open-still", "scale", "return-still"):
            if beat in first_start and span(beat) + 1e-6 < still_min:
                errors.append(f"evidence-dialogue {beat} must hold long enough to read")
    opens = [shot for shot in ready if shot.get("beat") == "open-still"]
    if opens and min(shot["start"] for shot in opens) > 1e-6:
        errors.append("evidence-dialogue must open on a still")
    returns = [shot for shot in ready if shot.get("beat") == "return-still"]
    if positive_number(duration) and returns and max(shot["end"] for shot in returns) < duration - 1e-6:
        errors.append("evidence-dialogue must end on a return still")
    motion = [(shot["start"], shot["end"]) for shot in ready if shot.get("beat") == "motion"]
    motion_total = union_seconds(motion)
    motion_min = spec.get("motion_seconds_min")
    ratio = spec.get("motion_ratio_min")
    floor = motion_min if positive_number(motion_min) else 0
    if positive_number(duration) and positive_number(ratio):
        floor = max(floor, ratio * duration)
    if motion and motion_total + 1e-6 < floor:
        errors.append("evidence-dialogue motion must be the main moving picture")


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
    if isinstance(video, dict) and "orientation" in video:
        orientation = video["orientation"]
        if not isinstance(orientation, str) or orientation not in {"landscape", "portrait", "square"}:
            errors.append("video.orientation must be landscape, portrait or square")
        elif "video" in sizes:
            width, height = sizes["video"]["width"], sizes["video"]["height"]
            expected = "landscape" if width > height else "portrait" if height > width else "square"
            if orientation != expected:
                errors.append("video.orientation differs from width and height")
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

    style_id, spec = resolve_style(data, errors, result)
    if style_id == "evidence-dialogue" and isinstance(spec, dict):
        validate_evidence_dialogue(data, shots, by_id, errors, warnings, spec)
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
