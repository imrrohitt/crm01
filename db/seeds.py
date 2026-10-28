"""
Database seeding.
Framework only — add your seed logic here.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_seeds() -> None:
    """Run seeds. Override in your application."""
    # Framework: no default data. Add your models and seed logic.
    print("Seeds: no-op (framework only). Add your seed logic in db/seeds.py.")
