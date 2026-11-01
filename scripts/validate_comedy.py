#!/usr/bin/env python3
"""Read-only checks for optional talking-painting comedy; no media generation."""

import argparse
from datetime import date
import json
import math
from pathlib import Path
import sys
from urllib.parse import urlparse

if __package__:
    from .validate_plan import validate_plan
else:
    from validate_plan import validate_plan


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def interval(item):
    start, end = item.get("start"), item.get("end")
    if (type(start) in (int, float) and type(end) in (int, float)
            and math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
        return start, end
    return None


def validate_comedy(data, base_dir, check_files=False, probe=False):
    report = validate_plan(data, base_dir, check_files, probe)
    errors, warnings = report["errors"], report["warnings"]
    performance = data.get("performance") if isinstance(data, dict) else None
    if not isinstance(performance, dict):
        errors.append("performance must be an object for comedy validation")
        return report
    if performance.get("mode") != "talking-painting-comedy":
        errors.append("performance.mode must be talking-painting-comedy")
    for field in ("premise", "detail", "conflict", "payoff"):
        if not nonempty(performance.get(field)):
            errors.append(f"performance.{field} is required")

    def objects(value, label):
        if not isinstance(value, list) or not value:
            errors.append(f"{label} must be a nonempty array")
            return []
        items = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                errors.append(f"{label}[{index}] must be an object")
            else:
                items.append(item)
        return items

    def indexed(items, label):
        result = {}
        for item in items:
            identifier = item.get("id")
            if not nonempty(identifier):
                errors.append(f"{label} needs a nonempty id")
            elif identifier in result:
                errors.append(f"duplicate {label} id: {identifier}")
            else:
                result[identifier] = item
        return result

    def lookup(items, key):
        return items.get(key) if isinstance(key, str) else None

    characters = indexed(objects(performance.get("characters"), "characters"), "character")
    if len(characters) < 2:
        errors.append("comedy needs at least two characters")
    for identifier, character in characters.items():
        for field in ("painting_location", "want", "tactic", "voice"):
            if not nonempty(character.get(field)):
                errors.append(f"character {identifier}.{field} is required")

    assets = indexed(objects(data.get("assets"), "assets"), "asset")
    shots = indexed(objects(data.get("shots"), "shots"), "shot")
    facts = indexed(objects(performance.get("facts"), "facts"), "fact")
    for identifier, fact in facts.items():
        for field in ("claim", "original_location"):
            if not nonempty(fact.get(field)):
                errors.append(f"fact {identifier}.{field} is required")
        source = fact.get("source_url")
        try:
            url = urlparse(source) if isinstance(source, str) else None
        except ValueError:
            url = None
        if url is None or url.scheme not in ("http", "https") or not url.netloc:
            errors.append(f"fact {identifier} needs a public source_url")
        try:
            accessed = fact.get("accessed_on")
            if not isinstance(accessed, str) or date.fromisoformat(accessed).isoformat() != accessed:
                raise ValueError
        except ValueError:
            errors.append(f"fact {identifier}.accessed_on must be YYYY-MM-DD")
        shot = lookup(shots, fact.get("evidence_shot_id"))
        asset = lookup(assets, shot.get("asset_id")) if shot else None
        if (not shot or shot.get("purpose") != "analysis"
                or not asset or asset.get("kind") != "original"):
            errors.append(f"fact {identifier} evidence must be an original analysis shot")

    for identifier, shot in shots.items():
        asset = lookup(assets, shot.get("asset_id"))
        if asset and asset.get("kind") in ("ai-image", "ai-video"):
            label = shot.get("ai_label")
            if not isinstance(label, str) or not any(
                    phrase in label for phrase in ("AI 想象演绎", "AI dramatization")):
                errors.append(f"shot {identifier} needs a readable AI dramatization label")

    lines = objects(performance.get("lines"), "lines")
    indexed(lines, "line")
    audible, visible, used_facts, times = set(), set(), set(), []
    for line in lines:
        label = f"line {line.get('id', '?')}"
        speaker = line.get("speaker")
        if lookup(characters, speaker) is None:
            errors.append(f"{label} references an unknown speaker")
        else:
            audible.add(speaker)
        for field in ("text", "delivery"):
            if not nonempty(line.get(field)):
                errors.append(f"{label}.{field} is required")
        kind = line.get("kind")
        if kind not in ("fiction", "fact"):
            errors.append(f"{label}.kind must be fiction or fact")
        refs = line.get("fact_ids", [])
        if not isinstance(refs, list):
            errors.append(f"{label}.fact_ids must be an array")
            refs = []
        if kind == "fact" and not refs:
            errors.append(f"{label} fact requires fact_ids")
        for ref in refs:
            if lookup(facts, ref) is None:
                errors.append(f"{label} references an unknown fact")
            else:
                used_facts.add(ref)
        shot = lookup(shots, line.get("shot_id"))
        if shot is None:
            errors.append(f"{label} references an unknown shot")
        line_time = interval(line)
        shot_time = interval(shot) if shot else None
        if not line_time:
            errors.append(f"{label} needs finite times with 0 <= start < end")
        else:
            times.append(line_time)
            if shot_time and (line_time[0] < shot_time[0] or line_time[1] > shot_time[1]):
                errors.append(f"{label} must stay within its shot")
        framing = line.get("framing")
        if framing not in ("on-screen", "off-screen"):
            errors.append(f"{label}.framing must be on-screen or off-screen")
        if framing == "on-screen":
            asset = lookup(assets, shot.get("asset_id")) if shot else None
            if (not asset or asset.get("kind") != "ai-video"
                    or shot.get("purpose") != "atmosphere"):
                errors.append(f"{label} on-screen speech must use ai-video atmosphere, not original evidence")
            elif lookup(characters, speaker) is not None:
                visible.add(speaker)
    ordered = sorted(times)
    covered_until = 0
    for start, end in ordered:
        if start < covered_until:
            errors.append("dialogue overlaps; separate turns for this single-speaker shot workflow")
        covered_until = max(covered_until, end)
    if len(audible) < 2 or len(visible) < 2:
        errors.append("at least two characters must speak on screen, not only narration")
    for identifier in facts.keys() - used_facts:
        errors.append(f"fact {identifier} is not linked to any dialogue line")
    warnings.append("Planning checks only: verify facts, image rights, humor, voices, lip sync and actual timing manually")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--check-files", action="store_true")
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.plan.read_text(encoding="utf-8"))
        report = validate_comedy(data, args.plan.resolve().parent, args.check_files, args.probe)
    except (OSError, ValueError) as exc:
        report = {"errors": [f"cannot read plan: {type(exc).__name__}"], "warnings": []}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
