#!/usr/bin/env python3
"""Command-line interface for the LTC Timecode Generator."""

import argparse
import os
import sys
from ltc_generator import FrameRate, LTCConfig, LTCGenerator


def parse_timecode(tc_str: str) -> tuple:
    """Parse a timecode string HH:MM:SS:FF into a tuple of ints."""
    parts = tc_str.split(":")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            f"Invalid timecode format '{tc_str}'. Expected HH:MM:SS:FF"
        )
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid timecode format '{tc_str}'. All fields must be integers."
        )


def parse_user_bits(value: str) -> int:
    """Parse a user bits hex string into an integer."""
    try:
        return int(value, 16)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid user-bits hex value '{value}'."
        )


def get_frame_rate_names() -> list:
    """Return all valid FrameRate enum names."""
    return [fr.name for fr in FrameRate]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LTC Timecode Generator - Command Line Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python cli.py --start 01:00:00:00 --duration 60 "
            "--frame-rate FR_29_97_DF --sample-rate 48000 --bit-depth 24 "
            "--output ltc_output.wav\n"
            "  python cli.py --start 00:00:00:00 --duration 10 "
            "--frame-rate FR_25_NDF --sample-rate 44100 --bit-depth 16 "
            "--output pal_test.wav --channels 2"
        ),
    )

    parser.add_argument(
        "--start", required=True, type=parse_timecode,
        help="Start timecode in HH:MM:SS:FF format"
    )
    parser.add_argument(
        "--duration", required=True, type=float,
        help="Duration in seconds"
    )
    parser.add_argument(
        "--frame-rate", required=True, choices=get_frame_rate_names(),
        help="Frame rate enum name (e.g. FR_29_97_DF, FR_25_NDF)"
    )
    parser.add_argument(
        "--sample-rate", required=True, type=int,
        choices=[44100, 48000, 96000, 192000],
        help="Audio sample rate in Hz"
    )
    parser.add_argument(
        "--bit-depth", required=True, type=int, choices=[16, 24],
        help="Audio bit depth"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output WAV file path"
    )
    parser.add_argument(
        "--channels", type=int, choices=[1, 2], default=1,
        help="Number of audio channels (default: 1)"
    )
    parser.add_argument(
        "--user-bits", type=parse_user_bits, default=0,
        help="User bits as hex string (default: 0)"
    )

    args = parser.parse_args()

    hours, minutes, seconds, frames = args.start

    # Resolve output path
    output_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Look up frame rate
    frame_rate = FrameRate.get_frame_rate_by_name(args.frame_rate)

    # Build config
    config = LTCConfig(
        frame_rate=frame_rate,
        sample_rate=args.sample_rate,
        bit_depth=args.bit_depth,
        start_time=(hours, minutes, seconds, frames),
        duration_seconds=args.duration,
    )

    # Generate
    generator = LTCGenerator(config)

    try:
        generator.export_wav(output_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Print summary
    tc = config.start_time
    print(f"LTC file generated successfully: {output_path}")
    print(f"  Start timecode : {tc[0]:02d}:{tc[1]:02d}:{tc[2]:02d}:{tc[3]:02d}")
    print(f"  Frame rate     : {frame_rate.get_display_name()} ({frame_rate.get_fps():.3f} fps)")
    print(f"  Sample rate    : {config.sample_rate} Hz")
    print(f"  Bit depth      : {config.bit_depth}-bit")
    print(f"  Duration       : {config.duration_seconds} seconds")
    print(f"  Channels       : {args.channels}")
    if args.user_bits:
        print(f"  User bits      : 0x{args.user_bits:08X}")


if __name__ == "__main__":
    main()
