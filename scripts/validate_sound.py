#!/usr/bin/env python3
"""Validate a sound cue/provenance plan; optional local media analysis. Python 3.9+."""

import argparse
from array import array
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qsl, urlsplit


SECRET_PARAMS = {"key", "api_key", "token", "access_token", "signature",
                 "x-amz-signature", "x-goog-signature", "authorization", "credential"}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def number(value, minimum=0):
    return type(value) in (int, float) and math.isfinite(value) and value >= minimum


def public_url(value):
    if not text(value):
        return False
    try:
        u = urlsplit(value)
        return (u.scheme in {"http", "https"} and bool(u.hostname)
                and not u.username and not u.password
                and not any(k.lower() in SECRET_PARAMS for k, _ in parse_qsl(u.query)))
    except ValueError:
        return False


def resolve(base, value):
    path = Path(value).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def probe_audio(path):
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe", "-select_streams", "a:0", "-show_streams",
         "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=30, check=False)
    if proc.returncode:
        raise ValueError("ffprobe could not read audio")
    data = json.loads(proc.stdout)
    if not data.get("streams"):
        raise ValueError("no audio stream")
    stream = data["streams"][0]
    duration = stream.get("duration") or data.get("format", {}).get("duration")
    try:
        duration = float(duration)
    except (TypeError, ValueError):
        raise ValueError("audio duration is unavailable")
    if not number(duration) or duration <= 0:
        raise ValueError("invalid audio duration")
    return {"duration_seconds": duration, "codec": stream.get("codec_name"),
            "sample_rate": stream.get("sample_rate"), "channels": stream.get("channels")}


def analyze_excerpt(path, start, end):
    # Stereo avoids cancellation of opposite-phase channels during mono downmix.
    proc = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-protocol_whitelist", "file,pipe",
         "-ss", str(start), "-i", str(path),
         "-t", str(end - start), "-vn", "-ac", "2", "-ar", "48000",
         "-f", "f32le", "-acodec", "pcm_f32le", "-"],
        capture_output=True, timeout=120, check=False)
    if proc.returncode or not proc.stdout:
        raise ValueError("ffmpeg could not decode the selected audio excerpt")
    samples = array("f")
    samples.frombytes(proc.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    if not all(math.isfinite(x) for x in samples):
        raise ValueError("decoded audio contains non-finite samples")
    peak = max(abs(x) for x in samples)
    rms = math.sqrt(sum(x * x for x in samples) / len(samples))
    # Relative -40 dB threshold is an energy locator, not a perceptual quality gate.
    threshold = peak * 0.01
    first = next((i for i, x in enumerate(samples) if abs(x) > threshold), None) if peak else None
    last = next((len(samples) - 1 - i for i, x in enumerate(reversed(samples))
                 if abs(x) > threshold), None) if peak else None
    db = lambda x: 20 * math.log10(x) if x else None
    return {"decoded_format": "48kHz stereo float",
            "source_excerpt_peak_dbfs": db(peak), "source_excerpt_rms_dbfs": db(rms),
            "first_energy_seconds": first // 2 / 48000 if first is not None else None,
            "last_energy_seconds": last // 2 / 48000 if last is not None else None,
            "energy_threshold_relative_db": -40, "silent": peak == 0}


def rights_issues(asset, usage):
    issues = []
    license_ = asset.get("license")
    if not isinstance(license_, dict):
        return ["license record is missing"]
    identifier = license_.get("id")
    try:
        date.fromisoformat(license_.get("checked_on", ""))
    except (TypeError, ValueError):
        issues.append("license checked_on date is missing/invalid (YYYY-MM-DD)")
    if license_.get("reviewed") is not True:
        issues.append("license/usage review is pending")
    if not text(identifier):
        issues.append("license id is unknown")
        return issues
    if identifier == "self-created":
        if not text(asset.get("author")) or not text(license_.get("usage_basis")):
            issues.append("self-created needs creator and usage_basis")
    elif identifier in {"provider-terms", "custom"}:
        if not public_url(license_.get("url")) or not text(license_.get("usage_basis")):
            issues.append("provider/custom terms need a URL and project usage_basis")
    elif identifier == "CC0-1.0":
        if not public_url(license_.get("url")):
            issues.append("CC0 needs its license URL")
    elif identifier in {f"CC-BY{suffix}-{v}" for suffix in ("", "-NC")
                        for v in ("2.0", "2.5", "3.0", "4.0")}:
        if "-NC-" in identifier and usage != "noncommercial":
            issues.append("NC material does not match public-release usage")
        if not all(text(asset.get(k)) for k in ("author", "title")):
            issues.append("attribution needs title and author")
        if not public_url(license_.get("url")) or not text(license_.get("attribution")):
            issues.append("attribution needs license URL and complete credit text")
    else:
        issues.append("unsupported/unknown license; document reviewed custom permission instead")
    return issues


def validate_sound(data, base_dir, ready=False, check_files=False, probe=False, analyze=False):
    errors, warnings, media, measurements = [], [], {}, {}
    result = {"errors": errors, "warnings": warnings, "media": media,
              "cue_measurements": measurements,
              "audition_verified_by_script": False, "network_access": False}
    if not isinstance(data, dict):
        errors.append("sound plan must be an object")
        return result
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        errors.append("schema_version must be 1")
    if data.get("status") not in ("draft", "ready"):
        errors.append("status must be draft or ready")
    strict = ready or data.get("status") == "ready"
    result["validation_mode"] = "ready" if strict else "draft"
    duration = data.get("duration_seconds")
    if not text(data.get("title")) or not number(duration) or duration <= 0:
        errors.append("title and positive duration_seconds are required")
    usage = data.get("usage")
    if usage not in ("public-release", "noncommercial"):
        errors.append("usage must be public-release or noncommercial")
    probe = probe or analyze or strict
    check_files = check_files or probe
    base = Path(base_dir)
    by_id, local = {}, {}
    assets = data.get("assets")
    if not isinstance(assets, list):
        errors.append("assets must be an array")
        assets = []
    for asset in assets:
        if not isinstance(asset, dict) or not text(asset.get("id")):
            errors.append("each asset needs an id")
            continue
        key = asset["id"]
        if key in by_id:
            errors.append(f"duplicate asset id: {key}")
        by_id[key] = asset
        if asset.get("origin") not in ("recorded", "generated"):
            errors.append(f"{key}: origin must be recorded or generated; reuse preserves origin")
        if asset.get("status") not in ("candidate", "selected", "rejected"):
            errors.append(f"{key}: invalid selection status")
        if not text(asset.get("title")):
            errors.append(f"{key}: title is required")
        if asset.get("source_url") is not None and not public_url(asset["source_url"]):
            errors.append(f"{key}: source_url must be HTTP(S) without credentials/signing tokens")
        review = asset.get("review", {})
        if not isinstance(review, dict) or review.get("audition") not in ("not-listened", "listened"):
            errors.append(f"{key}: explicitly record review.audition")
        elif review["audition"] == "not-listened":
            warnings.append(f"{key}: not auditioned; metadata and measurements are not listening")
    cues = data.get("cues")
    if not isinstance(cues, list):
        errors.append("cues must be an array")
        cues = []
    cue_ids, used = set(), set()
    for cue in cues:
        if not isinstance(cue, dict) or not text(cue.get("id")):
            errors.append("each cue needs an id")
            continue
        key = cue["id"]
        if key in cue_ids:
            errors.append(f"duplicate cue id: {key}")
        cue_ids.add(key)
        if cue.get("role") not in ("voice", "music", "ambience", "event") or not text(cue.get("intent")):
            errors.append(f"{key}: role and intent are required")
        aid = cue.get("asset_id")
        if not text(aid) or aid not in by_id:
            errors.append(f"{key}: unknown asset_id")
            continue
        used.add(aid)
        if by_id[aid].get("status") == "rejected":
            errors.append(f"{key}: rejected asset cannot be used")
        start, end = cue.get("start"), cue.get("end")
        si, so = cue.get("source_in"), cue.get("source_out")
        if not (number(start) and number(end) and start < end
                and number(duration) and end <= duration):
            errors.append(f"{key}: require 0 <= start < end <= duration_seconds")
            continue
        if not (number(si) and number(so) and si < so):
            errors.append(f"{key}: require 0 <= source_in < source_out")
            continue
        loop = cue.get("loop", False)
        if type(loop) is not bool:
            errors.append(f"{key}: loop must be boolean")
        if not loop and so - si > end - start + 0.001:
            errors.append(f"{key}: excerpt exceeds cue window; trim it instead of stretching")
        if loop:
            cross = cue.get("loop_crossfade", 0)
            if not number(cross) or not 0 < cross < (so - si) / 2:
                errors.append(f"{key}: loop_crossfade must be positive and less than half the excerpt")
        fade_in, fade_out = cue.get("fade_in", 0), cue.get("fade_out", 0)
        if not (number(fade_in) and number(fade_out)) or (
                fade_in + fade_out > (end - start if loop else so - si)):
            errors.append(f"{key}: fades exceed playable audio or are invalid")
        gain = cue.get("gain_db", 0)
        if type(gain) not in (int, float) or not math.isfinite(gain):
            errors.append(f"{key}: gain_db must be finite")
    for aid in sorted(used):
        asset = by_id[aid]
        license_record = asset.get("license") if isinstance(asset.get("license"), dict) else {}
        pending = rights_issues(asset, usage)
        if asset.get("status") != "selected":
            pending.append("used asset has not been selected")
        if not public_url(asset.get("source_url")) and license_record.get("id") != "self-created":
            pending.append("stable source page URL is missing")
        if asset.get("origin") == "generated" and (
                not text(asset.get("model")) or not text(asset.get("generation_record"))):
            pending.append("generated asset needs model and generation_record")
        if not text(asset.get("path")):
            pending.append("local path is missing")
        for problem in pending:
            (errors if strict else warnings).append(f"{aid}: {problem}")
        path = asset.get("path")
        if not check_files:
            continue
        if not text(path) or not resolve(base, path).is_file():
            errors.append(f"{aid}: local audio file does not exist")
            continue
        path = resolve(base, path)
        local[aid] = path
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        media[aid] = {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}
        if probe:
            try:
                media[aid].update(probe_audio(path))
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                errors.append(f"{aid}: {exc}")
    for cue in cues:
        if (not isinstance(cue, dict) or not text(cue.get("id"))
                or not text(cue.get("asset_id")) or cue["asset_id"] not in media):
            continue
        aid = cue["asset_id"]
        si, so = cue.get("source_in"), cue.get("source_out")
        if not (number(si) and number(so) and si < so):
            continue
        if "duration_seconds" in media[aid] and so > media[aid]["duration_seconds"] + 0.001:
            errors.append(f"{cue['id']}: source range exceeds actual audio duration")
            continue
        if analyze and "duration_seconds" in media[aid]:
            try:
                measurement = analyze_excerpt(local[aid], si, so)
                measurements[cue["id"]] = measurement
                if measurement["silent"]:
                    errors.append(f"{cue['id']}: selected excerpt is digital silence")
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                errors.append(f"{cue['id']}: {exc}")
    return result


def csv_text(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def write_cues(path, data):
    assets = {a["id"]: a for a in data["assets"]}
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "scene", "start_seconds", "end_seconds", "role", "intent",
                         "distance", "asset_id", "origin", "source_in", "source_out",
                         "gain_db", "ducking", "audition", "source_url"])
        for cue in data["cues"]:
            asset = assets[cue["asset_id"]]
            writer.writerow([
                csv_text(cue["id"]), csv_text(cue.get("scene", "")), cue["start"], cue["end"],
                cue["role"], csv_text(cue["intent"]), csv_text(cue.get("distance", "")),
                csv_text(asset["id"]), asset["origin"], cue["source_in"], cue["source_out"],
                cue.get("gain_db", 0), csv_text(cue.get("ducking", "")),
                asset["review"]["audition"], asset.get("source_url", "")])


def write_credits(path, data):
    used = {c["asset_id"] for c in data["cues"]}
    lines = [data["title"], "Sound sources (recorded/generated origin preserved):", ""]
    for asset in data["assets"]:
        if asset["id"] not in used:
            continue
        license_ = asset["license"]
        lines.append(f'{asset["title"]} — {asset.get("author", asset.get("provider", ""))}')
        lines.append(f'Origin: {asset["origin"]}; license/terms: {license_["id"]}')
        lines.extend(v for v in [asset.get("source_url"), license_.get("url"),
                                license_.get("attribution"), license_.get("usage_basis")] if text(v))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--ready", action="store_true", help="check selected files/provenance and probe audio; requires ffprobe")
    parser.add_argument("--check-files", action="store_true")
    parser.add_argument("--probe", action="store_true", help="implies --check-files; requires ffprobe")
    parser.add_argument("--analyze", action="store_true", help="implies --probe; requires ffmpeg")
    parser.add_argument("--report", type=Path, help="write JSON report, including the source plan")
    parser.add_argument("--cue-sheet", type=Path, help="write UTF-8 CSV when validation succeeds")
    parser.add_argument("--credits", type=Path, help="write credits; implies --ready")
    args = parser.parse_args()
    try:
        data = json.loads(args.plan.read_text(encoding="utf-8"))
        sources = {args.plan.resolve()}
        if isinstance(data, dict) and isinstance(data.get("assets"), list):
            sources.update(resolve(args.plan.parent, a["path"]) for a in data["assets"]
                           if isinstance(a, dict) and text(a.get("path")))
        outputs = [p.resolve() for p in (args.report, args.cue_sheet, args.credits) if p]
        if len(set(outputs)) != len(outputs) or set(outputs) & sources:
            raise ValueError("outputs must be distinct and cannot overwrite the plan or source audio")
        report = validate_sound(data, args.plan.parent, args.ready or bool(args.credits),
                                args.check_files, args.probe, args.analyze)
        report["source_plan"] = data
        if args.report:
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                                   encoding="utf-8")
        if not report["errors"]:
            if args.cue_sheet:
                write_cues(args.cue_sheet, data)
            if args.credits:
                write_credits(args.credits, data)
        print(json.dumps({k: v for k, v in report.items() if k != "source_plan"},
                         ensure_ascii=False, indent=2, allow_nan=False))
        return 1 if report["errors"] else 0
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"errors": [str(exc)]}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
