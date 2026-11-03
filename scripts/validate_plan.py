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
PURPOSES = {"analysis", "atmosphere", "title", "context"}
ANNOTATION_KINDS = {"underline", "circle", "highlight", "bracket"}
ANNOTATION_ROLES = {"year", "museum-credit", "quote", "label"}
ANNOTATION_KEYS = {"id", "kind", "role", "text", "source", "start", "end", "word_id"}
WORD_KEYS = {"id", "text", "start", "end"}
DESK_MATERIALS = {"map", "letter", "photo", "document"}
DESK_LAYERS = ["desk", "cutout", "occlusion"]
DESK_KEYS = {"material", "layers", "subject", "not_painting"}
TIMING_KEYS = {"camera", "elements_fps", "cut", "entrance", "follow_red_line"}
SOURCED_ROLES = {"year", "museum-credit", "quote"}


def positive_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def shot_refs(shot):
    if "asset_ids" in shot and isinstance(shot["asset_ids"], list):
        return shot["asset_ids"]
    return [shot.get("asset_id")]


def check_editorial(shot, label, pictures, purpose, errors, titles, video_fps, times_ok):
    """Optional citation marks and a non-painting evidence desk. Absent means unchanged."""
    generated = any(asset.get("kind") in ("ai-image", "ai-video") for asset in pictures)
    words = {}
    if "vo_words" in shot:
        entries = shot["vo_words"]
        if not isinstance(entries, list) or not entries:
            errors.append(f"{label}.vo_words must be a nonempty array")
            entries = []
        for index, word in enumerate(entries):
            word_label = f"{label}.vo_words[{index}]"
            if not isinstance(word, dict) or any(key not in WORD_KEYS for key in word):
                errors.append(f"{word_label} has unsupported fields")
                continue
            identifier = word.get("id")
            if not isinstance(identifier, str) or not identifier.strip() or identifier in words:
                errors.append(f"{word_label}.id must be a unique nonempty string")
            elif not isinstance(word.get("text"), str) or not word["text"].strip():
                errors.append(f"{word_label}.text is required")
            else:
                words[identifier] = word
            start, end = word.get("start"), word.get("end")
            if not finite_number(start) or not finite_number(end) or end <= start:
                errors.append(f"{word_label} needs finite times with start < end")
            elif times_ok and (start < shot["start"] or end > shot["end"]):
                errors.append(f"{word_label} must stay inside the shot")
    if "annotations" in shot:
        notes = shot["annotations"]
        if not isinstance(notes, list) or not notes:
            errors.append(f"{label}.annotations must be a nonempty array")
            notes = []
        if generated or purpose == "atmosphere":
            errors.append(f"{label} citations cannot sit on a generated shot")
        seen = set()
        for index, note in enumerate(notes):
            note_label = f"{label}.annotations[{index}]"
            if not isinstance(note, dict) or any(key not in ANNOTATION_KEYS for key in note):
                errors.append(f"{note_label} has unsupported fields")
                continue
            identifier = note.get("id")
            if not isinstance(identifier, str) or not identifier.strip() or identifier in seen:
                errors.append(f"{note_label}.id must be a unique nonempty string")
            else:
                seen.add(identifier)
            if note.get("kind") not in ANNOTATION_KINDS:
                errors.append(f"{note_label}.kind is unsupported")
            role = note.get("role")
            if role not in ANNOTATION_ROLES:
                errors.append(f"{note_label}.role is unsupported")
            text = note.get("text")
            if not isinstance(text, str) or not text.strip() or len(text.strip()) > 80:
                errors.append(f"{note_label}.text must be a short citation")
            if role in SOURCED_ROLES and (not isinstance(note.get("source"), str) or not note["source"].strip()):
                errors.append(f"{note_label}.source is required for {role}")
            if "source" in note and role not in SOURCED_ROLES:
                if not isinstance(note.get("source"), str) or not note["source"].strip():
                    errors.append(f"{note_label}.source must be a nonempty string")
            start, end = note.get("start"), note.get("end")
            if not finite_number(start) or not finite_number(end) or end <= start:
                errors.append(f"{note_label} needs finite times with start < end")
            elif times_ok and (start < shot["start"] or end > shot["end"]):
                errors.append(f"{note_label} must stay inside the shot")
            word_id = note.get("word_id")
            if word_id is not None:
                word = words.get(word_id)
                if not isinstance(word_id, str) or word is None:
                    errors.append(f"{note_label}.word_id must match a spoken word")
                elif finite_number(start) and finite_number(word.get("start")) and abs(start - word["start"]) > 1e-6:
                    errors.append(f"{note_label} must start when its spoken word starts")
    desk = shot.get("evidence_desk")
    if "evidence_desk" in shot:
        if not isinstance(desk, dict) or any(key not in DESK_KEYS for key in desk):
            errors.append(f"{label}.evidence_desk has unsupported fields")
        else:
            if desk.get("material") not in DESK_MATERIALS:
                errors.append(f"{label}.evidence_desk.material is unsupported")
            if desk.get("layers") != DESK_LAYERS:
                errors.append(f"{label}.evidence_desk.layers must be desk, cutout, occlusion")
            subject = desk.get("subject")
            if not isinstance(subject, str) or not subject.strip() or subject.strip() in titles:
                errors.append(f"{label}.evidence_desk.subject must name the archival item, not the painting")
            if desk.get("not_painting") is not True:
                errors.append(f"{label}.evidence_desk.not_painting must be true")
            if purpose != "context":
                errors.append(f"{label} evidence desk uses purpose context")
            if any(asset.get("kind") != "graphic" for asset in pictures):
                errors.append(f"{label} evidence desk only holds graphic archival scans")
    elif purpose == "context":
        errors.append(f"{label} context requires an evidence desk")
    if "editorial_timing" in shot:
        timing = shot["editorial_timing"]
        if not isinstance(timing, dict) or any(key not in TIMING_KEYS for key in timing):
            errors.append(f"{label}.editorial_timing has unsupported fields")
        else:
            if "camera" in timing and timing["camera"] != "smooth":
                errors.append(f"{label}.editorial_timing.camera must stay smooth")
            if "cut" in timing and timing["cut"] != "hard":
                errors.append(f"{label}.editorial_timing.cut must be a hard cut")
            if "entrance" in timing and timing["entrance"] != "spring":
                errors.append(f"{label}.editorial_timing.entrance must be spring")
            element_fps = timing.get("elements_fps")
            if "elements_fps" in timing and (
                    not positive_number(element_fps) or element_fps < 8 or element_fps > 15
                    or (video_fps is not None and element_fps >= video_fps)):
                errors.append(f"{label}.editorial_timing.elements_fps must be coarser than the camera, around 12")
            if "follow_red_line" in timing and type(timing["follow_red_line"]) is not bool:
                errors.append(f"{label}.editorial_timing.follow_red_line must be boolean")
    if "music_duck" in shot and type(shot["music_duck"]) is not bool:
        errors.append(f"{label}.music_duck must be boolean")
    timing = shot.get("editorial_timing")
    return bool(isinstance(timing, dict) and timing.get("follow_red_line") is True and times_ok)


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
    multi = "artworks" in data
    works = {}
    if multi:
        if "artwork" in data:
            errors.append("use artworks or the legacy artwork, not both")
        entries = data["artworks"]
        if not isinstance(entries, list) or len(entries) < 2:
            errors.append("artworks needs at least two works")
            entries = entries if isinstance(entries, list) else []
        for index, work in enumerate(entries):
            label = f"artworks[{index}]"
            if not isinstance(work, dict):
                errors.append(f"{label} must be an object")
                continue
            identifier = work.get("id")
            if not isinstance(identifier, str) or not identifier.strip():
                errors.append(f"{label}.id is required")
                continue
            if identifier in works:
                errors.append(f"duplicate artwork id: {identifier}")
            works[identifier] = work
            for field in ("title", "artist"):
                if not isinstance(work.get(field), str) or not work[field].strip():
                    errors.append(f"{label}.{field} is required")
            sources = work.get("sources")
            if (not isinstance(sources, list) or not sources
                    or any(not isinstance(x, str) or not x.strip() for x in sources)):
                errors.append(f"{label}.sources needs source references")
        comparison = data.get("comparison")
        if not isinstance(comparison, dict):
            errors.append("multi-work plan needs comparison")
        else:
            if comparison.get("mode") not in ("same-artist", "cross-artist", "relationships"):
                errors.append("comparison.mode is unsupported")
            if not isinstance(comparison.get("question"), str) or not comparison["question"].strip():
                errors.append("comparison.question is required")
            axes = comparison.get("axes")
            if (not isinstance(axes, list) or not axes
                    or any(not isinstance(x, str) or not x.strip() for x in axes)):
                errors.append("comparison.axes needs nonempty comparison axes")
    else:
        artwork = data.get("artwork")
        if not isinstance(artwork, dict) or not isinstance(artwork.get("title"), str) or not artwork["title"].strip():
            errors.append("artwork.title is required")
        elif not isinstance(artwork.get("sources"), list) or not artwork["sources"]:
            warnings.append("artwork.sources has no references; verify provenance separately")
    if "editing_style" in data and data["editing_style"] not in ("contemplative", "playful-art-history"):
        errors.append("editing_style is unsupported")

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
        if multi and asset.get("kind") in ("original", "ai-image", "ai-video"):
            work_id = asset.get("artwork_id")
            if not isinstance(work_id, str) or work_id not in works:
                errors.append(f"{label} must bind a declared artwork_id")
        if check_files or probe:
            local_file(asset.get("path"), label)
        elif not asset.get("path"):
            warnings.append(f"{label} has no local path (planning only)")

    shots = data.get("shots")
    if not isinstance(shots, list) or not shots:
        errors.append("shots must be a nonempty array")
        shots = []
    titles = set()
    if multi:
        titles.update(work.get("title", "").strip() for work in works.values() if isinstance(work.get("title"), str))
    elif isinstance(data.get("artwork"), dict) and isinstance(data["artwork"].get("title"), str):
        titles.add(data["artwork"]["title"].strip())
    video_fps = fps if positive_number(fps) else None
    intervals, shot_ids, follow_lines = [], set(), []
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
        if "asset_ids" in shot:
            refs = shot["asset_ids"]
            if ("asset_id" in shot or not isinstance(refs, list) or not refs
                    or any(not isinstance(x, str) for x in refs)):
                errors.append(f"{label} needs asset_id or a nonempty asset_ids array, not both")
                continue
            if len(refs) != len(set(refs)):
                errors.append(f"{label} has duplicate asset references")
        else:
            refs = [shot.get("asset_id")]
        pictures = [by_id[x] for x in refs if isinstance(x, str) and x in by_id]
        if len(pictures) != len(refs):
            errors.append(f"{label} references an unknown asset")
            continue
        purpose = shot.get("purpose")
        if not isinstance(purpose, str) or purpose not in PURPOSES:
            errors.append(f"{label}.purpose is unsupported")
        if purpose == "analysis" and any(a.get("kind") != "original" for a in pictures):
            errors.append(f"{label} analysis must reference original artwork")
        if any(a.get("kind") == "audio" for a in pictures):
            errors.append(f"{label} primary picture cannot be an audio asset")
        if any(a.get("kind") in ("ai-image", "ai-video") for a in pictures):
            label_text = shot.get("ai_label")
            if not isinstance(label_text, str) or not label_text.strip():
                errors.append(f"{label} generated picture requires ai_label")
        identities = {a["artwork_id"] for a in pictures
                      if isinstance(a.get("artwork_id"), str)}
        if multi and purpose == "analysis" and len(identities) > 1:
            axis, labels = shot.get("comparison_axis"), shot.get("labels")
            if not isinstance(axis, str) or not axis.strip():
                errors.append(f"{label} needs comparison_axis for a multi-work comparison")
            if not isinstance(labels, dict) or any(
                    not isinstance(labels.get(k), str) or not labels[k].strip() for k in identities):
                errors.append(f"{label} must label each compared artwork")
        times_ok = (type(start) in (int, float) and math.isfinite(start) and start >= 0
                    and positive_number(end) and end > start)
        if check_editorial(shot, label, pictures, purpose, errors, titles, video_fps, times_ok):
            follow_lines.append((label, end))
    for label, end in follow_lines:
        followers = []
        for shot in shots:
            if not isinstance(shot, dict):
                continue
            start = shot.get("start")
            follower_end = shot.get("end")
            if not (finite_number(start) and positive_number(follower_end)):
                continue
            if start <= end + 1e-6 and follower_end > end + 1e-6:
                followers.append(shot)
        if len(followers) != 1:
            errors.append(f"{label} follow_red_line needs one following shot")
            continue
        follower = followers[0]
        if follower.get("purpose") != "analysis":
            errors.append(f"{label} follow_red_line must cut to an original analysis shot")
            continue
        refs = [item for item in shot_refs(follower) if isinstance(item, str)]
        if not refs or any(by_id.get(item, {}).get("kind") != "original" for item in refs):
            errors.append(f"{label} follow_red_line must cut to the hi-res painting")
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
