#!/usr/bin/env python3
"""Small, allow-listed FFmpeg interface for the shared video workspace."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKSPACE = Path(os.environ.get("VIDEO_WORKSPACE", "/workspace/videos")).resolve()
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


def safe_path(value, *, output=False):
    path = Path(value)
    if path.is_absolute():
        candidate = path.resolve(strict=False)
    else:
        candidate = (WORKSPACE / path).resolve(strict=False)
    try:
        candidate.relative_to(WORKSPACE)
    except ValueError as exc:
        raise ValueError("la ruta debe permanecer dentro de /workspace/videos") from exc
    if output:
        if candidate == WORKSPACE or candidate.name in {".", ".."}:
            raise ValueError("salida inválida")
        candidate.parent.mkdir(parents=True, exist_ok=True)
    elif not candidate.is_file():
        raise ValueError(f"entrada inexistente: {candidate.name}")
    return candidate


def atomic_output(destination, command):
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.stem}.", suffix=destination.suffix,
                                     dir=destination.parent)
    os.close(fd)
    temporary_path = Path(temporary)
    try:
        subprocess.run(command + [str(temporary_path)], check=True)
        os.replace(temporary_path, destination)
    except (OSError, subprocess.CalledProcessError):
        temporary_path.unlink(missing_ok=True)
        raise


def probe(args):
    source = safe_path(args.input)
    command = ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(source)]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    if args.output:
        destination = safe_path(args.output, output=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
        os.close(fd)
        temporary_path = Path(temporary)
        try:
            temporary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)
    else:
        print(json.dumps(payload, ensure_ascii=True, indent=2))


def media_command(args):
    source = safe_path(args.input)
    destination = safe_path(args.output, output=True)
    if args.command == "prepare_video":
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                   "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
                   "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart"]
    elif args.command == "extract_audio":
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                   "-map", "0:a:0", "-vn", "-c:a", "libmp3lame", "-q:a", "2"]
    elif args.command == "export_reel":
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                   "-t", "60", "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264",
                   "-c:a", "aac", "-movflags", "+faststart"]
    else:
        audio = safe_path(args.audio)
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                   "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                   "-c:a", "aac", "-shortest", "-movflags", "+faststart"]
    atomic_output(destination, command)
    print(destination.relative_to(WORKSPACE))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="video-tool")
    sub = parser.add_subparsers(dest="command", required=True)
    probe_parser = sub.add_parser("probe")
    probe_parser.add_argument("input")
    probe_parser.add_argument("--output")
    for command in ("prepare_video", "extract_audio", "export_reel"):
        item = sub.add_parser(command)
        item.add_argument("input")
        item.add_argument("output")
    mixer = sub.add_parser("mix_audio")
    mixer.add_argument("input")
    mixer.add_argument("audio")
    mixer.add_argument("output")
    args = parser.parse_args(argv)
    try:
        probe(args) if args.command == "probe" else media_command(args)
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"video-tool: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
