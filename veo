#!/usr/bin/env python3
"""Generate videos via Google's Veo 3.1 Lite model."""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

MODEL = "veo-3.1-lite-generate-preview"


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "Generate videos with Google's Veo 3.1 Lite model. Supports "
            "text-to-video, image-to-video (first frame), and first+last "
            "frame interpolation with configurable aspect ratio, duration, "
            "and resolution."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("prompt", help="Text prompt describing the video to generate.")
    p.add_argument(
        "-o", "--output-dir", required=True,
        help="Directory to write generated MP4 into. Created if missing.",
    )
    p.add_argument(
        "-a", "--aspect-ratio", choices=["16:9", "9:16"], default="16:9",
        help="Video aspect ratio.",
    )
    p.add_argument(
        "-d", "--duration", choices=["4", "6", "8"], default="8",
        help="Video duration in seconds.",
    )
    p.add_argument(
        "-s", "--resolution", choices=["720p", "1080p"], default="720p",
        help="Video resolution. Constraint: 1080p requires --duration=8.",
    )
    p.add_argument(
        "-i", "--image", default=None, metavar="PATH",
        help="Path to a first-frame image for image-to-video generation.",
    )
    p.add_argument(
        "-l", "--last-frame", default=None, metavar="PATH",
        help="Path to a last-frame image for interpolation. Constraint: requires --image.",
    )
    p.add_argument(
        "-p", "--person-generation",
        choices=["allow_all", "allow_adult", "dont_allow"], default=None,
        help="Controls generation of people.",
    )
    p.add_argument(
        "-n", "--name", default=None,
        help="Output filename stem (no extension). Defaults to a timestamp.",
    )
    p.add_argument(
        "--poll-interval", type=int, default=10,
        help="Seconds between status polls while waiting for generation.",
    )
    return p.parse_args()


def main():
    args = parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("error: GEMINI_API_KEY is not set in the environment.")

    if args.last_frame and not args.image:
        sys.exit("error: --last-frame requires --image.")

    if args.resolution == "1080p" and args.duration != "8":
        sys.exit("error: 1080p resolution requires duration=8.")

    image_path = Path(args.image).expanduser() if args.image else None
    last_frame_path = Path(args.last_frame).expanduser() if args.last_frame else None

    if image_path and not image_path.is_file():
        sys.exit(f"error: image not found: {image_path}")
    if last_frame_path and not last_frame_path.is_file():
        sys.exit(f"error: last-frame image not found: {last_frame_path}")

    out_dir = Path(args.output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    from google import genai
    from google.genai import types

    client = genai.Client()

    # Build config.
    config_kwargs = {
        "aspect_ratio": args.aspect_ratio,
        "duration_seconds": int(args.duration),
        "resolution": args.resolution,
    }
    if args.person_generation:
        config_kwargs["person_generation"] = args.person_generation

    # Load images if provided.
    image = None
    if image_path:
        from PIL import Image
        image = Image.open(image_path)

    if last_frame_path:
        from PIL import Image as PILImage
        config_kwargs["last_frame"] = PILImage.open(last_frame_path)

    config = types.GenerateVideosConfig(**config_kwargs)

    # Submit generation request.
    generate_kwargs = {
        "model": MODEL,
        "prompt": args.prompt,
        "config": config,
    }
    if image is not None:
        generate_kwargs["image"] = image

    operation = client.models.generate_videos(**generate_kwargs)

    # Poll until done.
    while not operation.done:
        print(f"Waiting for video generation... (polling every {args.poll_interval}s)")
        time.sleep(args.poll_interval)
        operation = client.operations.get(operation)

    stem = args.name or datetime.now().strftime("veo-%Y%m%d-%H%M%S")
    path = out_dir / f"{stem}.mp4"

    video = operation.response.generated_videos[0]
    client.files.download(file=video.video)
    video.video.save(str(path))

    print(path)


if __name__ == "__main__":
    main()
