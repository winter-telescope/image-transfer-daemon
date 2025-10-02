#!/usr/bin/env python3
"""Simple script to install the image transfer daemon as a service."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from image_transfer.services import main

if __name__ == "__main__":
    main()
