from __future__ import annotations

import unittest

from src.core import MissionThreadIsolator, run


class IsoTests(unittest.TestCase):
    def test_no_direct_leak(self) -> None:
        r = run({"secret": 42})
        self.assertFalse(r["leaked_direct"])
        self.assertEqual(r["imported"], 42)

    def test_bad_authority(self) -> None:
        iso = MissionThreadIsolator()
        iso.open("m1", "tok1")
        with self.assertRaises(PermissionError):
            iso.write("m1", "wrong", "k", 1)


if __name__ == "__main__":
    unittest.main()
