"""Shared pytest configuration.

Ensures the repository root is importable so ``import engine`` and
``import memory`` work whether or not the backend editable install is present.
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
