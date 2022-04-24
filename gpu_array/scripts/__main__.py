#! /usr/bin/env python

import argparse
import subprocess
from gpu_array.query import *
from gpu_array.tui import *


def parse_cli():
    parser = argparse.ArgumentParser(description="Tool for visual GPU monitoring")
    parser.add_argument(
        "--cardwidth", type=int, default=35, help="Width of each visual GPU card"
    )
    return parser


def main():
    try:
        subprocess.run(["nvidia-smi"])
    except:
        raise RuntimeError("nvidia-smi not currently installed")

    parser = parse_cli()
    cli_args = parser.parse_args()
    query = GPUQuery()
    tracker = Tracker(query)
    front = FrontEnd(tracker, card_width=cli_args.cardwidth)
    front.start()


if __name__ == "__main__":
    main()
