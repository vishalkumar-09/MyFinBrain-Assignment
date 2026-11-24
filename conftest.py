"""
conftest.py – Pytest configuration and shared fixtures.
"""
import sys
import os

# Ensure the project root is always importable
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
