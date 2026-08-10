from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from humain_api import content_hash


def main() -> None:
    examples = sorted((ROOT / "examples").glob("*.json"))
    for path in examples:
        json.loads(path.read_text())
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful(): raise SystemExit(1)
    print(f"verified examples={len(examples)} tests={result.testsRun} hash={content_hash({'protocol':'humain','version':'0.1'})}")


if __name__ == "__main__": main()
