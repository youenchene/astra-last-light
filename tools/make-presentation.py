#!/usr/bin/env python3
"""Host entry point for the generator also available in the game-only build."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[1] /
                       'game/tools/make-presentation.py'), run_name='__main__')
