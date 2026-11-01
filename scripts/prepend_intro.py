#!/usr/bin/env python3
"""Prepend a ready-made intro, preserve episode geometry, and shift companion SRT."""

import argparse
from fractions import Fraction
import json
import re
import shutil
import subprocess
from pathlib import Path
import tempfile

DEFAULT_INTRO = Path(__file__).resolve().parents[1] / 'assets/series-intro/intro-4s-v2.mp4'
TIMESTAMP = re.compile(r'(\d{2,}):(\d{2}):(\d{2}),(\d{3})')


def probe(path):
    data = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)
    ], text=True))
    video = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
    if video is None:
        raise ValueError(f'No video stream: {path}')
    # Container duration may include AAC padding. Use the video timeline.
    duration = video.get('duration')
    if duration in (None, 'N/A') and video.get('duration_ts') is not None:
        duration = Fraction(video['duration_ts']) * Fraction(video['time_base'])
    if duration in (None, 'N/A'):
        raise ValueError(f'No reliable video duration: {path}')
    rate = Fraction(video.get('avg_frame_rate', '0/1'))
    if rate <= 0 or Fraction(duration) <= 0:
        raise ValueError(f'Invalid video timing: {path}')
    return dict(width=video['width'], height=video['height'], fps=rate,
                duration=Fraction(duration), frames=video.get('nb_frames'),
                audio=any(s['codec_type'] == 'audio' for s in data['streams']))


def plan_join(intro, episode, overlap_frames):
    if intro['width'] * episode['height'] != episode['width'] * intro['height']:
        raise ValueError('Aspect ratios differ; recompose the intro before joining')
    if episode['width'] % 2 or episode['height'] % 2:
        raise ValueError('H.264 yuv420p output requires even dimensions')
    if overlap_frames < 0:
        raise ValueError('overlap-frames cannot be negative')
    fps = episode['fps']
    intro_frames = round(intro['duration'] * fps)
    episode_frames = round(episode['duration'] * fps)
    if min(intro_frames, episode_frames) <= overlap_frames:
        raise ValueError('Overlap must be shorter than both videos')
    offset_frames = intro_frames - overlap_frames
    return dict(fps=fps, intro_frames=intro_frames, episode_frames=episode_frames,
                offset=Fraction(offset_frames, 1) / fps,
                duration=Fraction(offset_frames + episode_frames, 1) / fps,
                frames=offset_frames + episode_frames,
                overlap=Fraction(overlap_frames, 1) / fps)


def shift_srt(text, offset):
    def replace(match):
        hours, minutes, seconds, millis = map(int, match.groups())
        if minutes > 59 or seconds > 59:
            raise ValueError('Invalid SRT timestamp')
        total = ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis
        total += round(offset * 1000)
        return f'{total // 3600000:02d}:{total // 60000 % 60:02d}:{total // 1000 % 60:02d},{total % 1000:03d}'
    if not TIMESTAMP.search(text):
        raise ValueError('No SRT timestamps found')
    return TIMESTAMP.sub(replace, text)


def decimal(value):
    return f'{float(value):.9f}'.rstrip('0').rstrip('.')


def filter_graph(intro, episode, plan):
    fps = str(plan['fps'])
    timebase = str(1 / plan['fps'])
    w, h = episode['width'], episode['height']
    filters = []
    for i, source in enumerate((intro, episode)):
        frames = plan['intro_frames'] if i == 0 else plan['episode_frames']
        filters.append(f'[{i}:v]scale={w}:{h}:flags=lanczos,setsar=1,fps={fps},'
                       f'trim=end_frame={frames},settb=expr={timebase},'
                       f'setpts=PTS-STARTPTS,format=yuv420p[v{i}]')
        duration = decimal(Fraction(frames, 1) / plan['fps'])
        audio = (f'[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,'
                 'asetpts=PTS-STARTPTS,apad' if source['audio'] else
                 'anullsrc=r=48000:cl=stereo')
        filters.append(f'{audio},atrim=duration={duration}[a{i}]')
    if plan['overlap']:
        overlap = decimal(plan['overlap'])
        filters += [f'[v0][v1]xfade=transition=fade:duration={overlap}:'
                    f'offset={decimal(plan["offset"])}[v]',
                    f'[a0][a1]acrossfade=d={overlap}:c1=tri:c2=tri[a]']
    else:
        filters += ['[v0][v1]concat=n=2:v=1:a=0[v]', '[a0][a1]concat=n=2:v=0:a=1[a]']
    return ';'.join(filters)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--intro', type=Path, default=DEFAULT_INTRO)
    parser.add_argument('--episode', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--overlap-frames', type=int, default=6)
    parser.add_argument('--subtitles', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        if not all(shutil.which(tool) for tool in ('ffmpeg', 'ffprobe')):
            raise ValueError('FFmpeg and ffprobe are required')
        intro_path, episode_path, output = (p.expanduser().resolve() for p in
                                           (args.intro, args.episode, args.output))
        if not intro_path.is_file() or not episode_path.is_file():
            raise ValueError('Both input videos must exist')
        if output.suffix.lower() != '.mp4':
            raise ValueError('Output must have .mp4 extension')
        if not output.parent.is_dir():
            raise ValueError('Create the output directory first')
        report_path = output.with_suffix('.join.json')
        srt_path = output.with_suffix('.srt') if args.subtitles else None
        inputs = {intro_path, episode_path}
        if args.subtitles:
            inputs.add(args.subtitles.expanduser().resolve())
        targets = [output, report_path] + ([srt_path] if srt_path else [])
        if any(p in inputs or p.exists() for p in targets):
            raise ValueError('Use fresh output paths; inputs and existing outputs are never overwritten')
        intro, episode = probe(intro_path), probe(episode_path)
        plan = plan_join(intro, episode, args.overlap_frames)
        subtitles = (shift_srt(args.subtitles.expanduser().read_text(encoding='utf-8-sig'),
                               plan['offset']) if args.subtitles else None)
        report = dict(intro=str(intro_path), episode=str(episode_path), output=str(output),
                      width=episode['width'], height=episode['height'], fps=str(plan['fps']),
                      frames=plan['frames'], duration_seconds=float(plan['duration']),
                      overlap_frames=args.overlap_frames,
                      episode_offset_seconds=float(plan['offset']),
                      subtitles=str(srt_path) if srt_path else None,
                      render_tool='FFmpeg', native_editor_project_updated=False)
        if args.dry_run:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        with tempfile.TemporaryDirectory(prefix='.intro-join-', dir=output.parent) as temp:
            temp_video = Path(temp) / 'joined.mp4'
            command = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                       '-filter_complex_threads', '1', '-i', str(intro_path), '-i', str(episode_path),
                       '-filter_complex', filter_graph(intro, episode, plan), '-map', '[v]', '-map', '[a]',
                       '-t', decimal(plan['duration']), '-c:v', 'libx264', '-preset', 'fast',
                       '-crf', '18', '-pix_fmt', 'yuv420p', '-threads', '2', '-c:a', 'aac',
                       '-b:a', '192k', '-movflags', '+faststart', str(temp_video)]
            subprocess.run(command, check=True)
            measured = probe(temp_video)
            if int(measured.get('frames') or 0) != plan['frames'] or not measured['audio']:
                raise ValueError('Rendered frame count or audio stream differs from plan')
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(temp_video), '-f', 'null', '-'], check=True)
            report['full_decode_passed'] = True
            report['subjective_audio_audition'] = False
            if subtitles is not None:
                srt_path.write_text(subtitles, encoding='utf-8')
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            temp_video.replace(output)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'{type(exc).__name__}: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
