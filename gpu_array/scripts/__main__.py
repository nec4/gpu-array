#! /usr/bin/env python

from gpu_array.query import *
from gpu_array.tui import *


def main():
    query = GPUQuery()
    tracker = Tracker(query)
    front = FrontEnd(tracker)
    front.start()

if __name__ == "__main__":
    main()
