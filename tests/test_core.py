
from __future__ import annotations
import threading
import unittest
from src.core import MissionThreadIsolator, run


class IsoLeveledTests(unittest.TestCase):
    def test_no_direct_leak(self) -> None:
        r = run({"secret": 42})
        self.assertFalse(r["leaked_direct"])
        self.assertEqual(r["imported"], 42)

    def test_bad_authority(self) -> None:
        iso = MissionThreadIsolator()
        iso.open("m1", "tok1")
        with self.assertRaises(PermissionError):
            iso.write("m1", "wrong", "k", 1)

    def test_export_expiry(self) -> None:
        iso = MissionThreadIsolator()
        iso.open("m1", "tok1")
        iso.open("m2", "tok2")
        iso.write("m1", "tok1", "k", 7)
        eid = iso.export("m1", "tok1", "k", now=10.0, ttl_s=5.0)
        with self.assertRaises(PermissionError):
            iso.import_export("m2", "tok2", eid, "x", now=20.0)

    def test_single_use_export(self) -> None:
        iso = MissionThreadIsolator()
        iso.open("m1", "tok1")
        iso.open("m2", "tok2")
        iso.open("m3", "tok3")
        iso.write("m1", "tok1", "k", 1)
        eid = iso.export("m1", "tok1", "k", now=0.0, single_use=True)
        iso.import_export("m2", "tok2", eid, "x", now=1.0)
        with self.assertRaises(PermissionError):
            iso.import_export("m3", "tok3", eid, "y", now=2.0)

    def test_revoke(self) -> None:
        iso = MissionThreadIsolator()
        iso.open("m1", "tok1")
        iso.open("m2", "tok2")
        iso.write("m1", "tok1", "k", 1)
        eid = iso.export("m1", "tok1", "k", now=0.0)
        iso.revoke_export("m1", "tok1", eid)
        with self.assertRaises(PermissionError):
            iso.import_export("m2", "tok2", eid, "x", now=1.0)

    def test_close_revokes_exports(self) -> None:
        iso = MissionThreadIsolator()
        iso.open("m1", "tok1")
        iso.open("m2", "tok2")
        iso.write("m1", "tok1", "k", 1)
        eid = iso.export("m1", "tok1", "k", now=0.0)
        iso.close("m1", "tok1")
        with self.assertRaises(PermissionError):
            iso.import_export("m2", "tok2", eid, "x", now=1.0)

    def test_self_import_useless(self) -> None:
        iso = MissionThreadIsolator()
        iso.open("m1", "tok1")
        iso.write("m1", "tok1", "k", 1)
        eid = iso.export("m1", "tok1", "k", now=0.0)
        with self.assertRaises(ValueError):
            iso.import_export("m1", "tok1", eid, "x", now=1.0)

    def test_concurrent_writes_same_thread(self) -> None:
        iso = MissionThreadIsolator()
        iso.open("m1", "tok1")

        def w(i: int) -> None:
            iso.write("m1", "tok1", "k", i)

        threads = [threading.Thread(target=w, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # last writer wins; no crash / corruption of dict structure
        self.assertIn(iso.read("m1", "tok1", "k"), set(range(50)))


if __name__ == "__main__":
    unittest.main()
