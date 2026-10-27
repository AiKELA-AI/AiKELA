#!/usr/bin/env python3
"""Compatibility entry point for the unified POP activity extractor.

The former game-only extraction is archived under
archive/pop-legacy-game-candidates/. Use the unified extractor to regenerate
games, yarns, crafts and the complete activity catalogue.
"""

from extract_pop_activities import main


if __name__ == "__main__":
    main()
