"""Mission thread isolator — no cross-thread shared mutable authority."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


def digest(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


@dataclass
class ThreadContext:
    thread_id: str
    authority_token: str
    state: dict = field(default_factory=dict)


class MissionThreadIsolator:
    """Each mission thread owns isolated state; cross-reads require explicit export grant."""

    def __init__(self) -> None:
        self._threads: dict[str, ThreadContext] = {}
        self._exports: dict[str, dict] = {}

    def open(self, thread_id: str, authority_token: str) -> None:
        if thread_id in self._threads:
            raise ValueError("THREAD_EXISTS")
        self._threads[thread_id] = ThreadContext(thread_id, authority_token)

    def write(self, thread_id: str, authority_token: str, key: str, value: object) -> None:
        t = self._require(thread_id, authority_token)
        t.state[key] = value

    def read(self, thread_id: str, authority_token: str, key: str) -> object:
        t = self._require(thread_id, authority_token)
        return t.state.get(key)

    def export(self, thread_id: str, authority_token: str, key: str) -> str:
        t = self._require(thread_id, authority_token)
        if key not in t.state:
            raise KeyError("MISSING_KEY")
        export_id = digest({"t": thread_id, "k": key, "v": t.state[key]})[:16]
        self._exports[export_id] = {
            "from": thread_id,
            "key": key,
            "value": t.state[key],
        }
        return export_id

    def import_export(
        self, thread_id: str, authority_token: str, export_id: str, as_key: str
    ) -> None:
        t = self._require(thread_id, authority_token)
        if export_id not in self._exports:
            raise KeyError("UNKNOWN_EXPORT")
        payload = self._exports[export_id]
        if payload["from"] == thread_id:
            raise ValueError("SELF_IMPORT_USELESS")
        t.state[as_key] = payload["value"]

    def _require(self, thread_id: str, authority_token: str) -> ThreadContext:
        t = self._threads.get(thread_id)
        if t is None:
            raise KeyError("UNKNOWN_THREAD")
        if t.authority_token != authority_token:
            raise PermissionError("BAD_AUTHORITY")
        return t


def run(example_input: dict) -> dict:
    iso = MissionThreadIsolator()
    iso.open("m1", "tok1")
    iso.open("m2", "tok2")
    secret = example_input.get("secret", 1)
    iso.write("m1", "tok1", "secret", secret)
    # Isolation: m2 has no key — returns None, never m1's value without export.
    leaked = iso.read("m2", "tok2", "secret") == secret
    eid = iso.export("m1", "tok1", "secret")
    iso.import_export("m2", "tok2", eid, "imported")
    return {
        "leaked_direct": leaked,
        "imported": iso.read("m2", "tok2", "imported"),
        "export_id": eid,
    }
