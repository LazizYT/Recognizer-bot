# Ensure project root is on sys.path so top-level packages (services, tasks, storage, etc.) are importable during tests
import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root not in sys.path:
    sys.path.insert(0, root)
