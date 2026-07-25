"""Pytest configuration — makes the seo_audit package importable in tests."""
import sys
from pathlib import Path

# Add the project root to sys.path so that `import seo_audit` works.
sys.path.insert(0, str(Path(__file__).parent))
