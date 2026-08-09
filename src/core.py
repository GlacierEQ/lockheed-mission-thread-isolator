
"""Mission thread isolator — no cross-thread shared mutable authority.

Leveled (L1): export TTL + half-life, single-use optional exports,
authority binding, export revoke, deterministic export IDs.

Independent reference only — no employer affiliation claimed.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any


def digest(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


@dataclass
class ThreadContext:
    thread_id: str
    authority_token: str
    state: dict[str, Any] = field(default_factory=dict)
    opened_at: float = 0.0


@dataclass
class ExportGrant:
    export_id: str
    from_thread: str
    key: str
    value: Any
    not_after: float
    single_use: bool
    consumed: bool = False
    revoked: bool = False


class MissionThreadIsolator:
    """Each mission thread owns isolated state; cross-reads require explicit export grants."""

    def __init__(self, default_export_ttl_s: float = 60.0) -> None:
        if default_export_ttl_s <= 0:
            raise ValueError("default_export_ttl_s must be positive")
        self._threads: dict[str, ThreadContext] = {}
        self._exports: dict[str, ExportGrant] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_export_ttl_s

    def open(self, thread_id: str, authority_token: str, now: float | None = None) -> None:
        t = time.time() if now is None else now
        with self._lock:
            if thread_id in self._threads:
                raise ValueError("THREAD_EXISTS")
            if not authority_token:
                raise ValueError("EMPTY_AUTHORITY")
            self._threads[thread_id] = ThreadContext(thread_id, authority_token, {}, t)

    def close(self, thread_id: str, authority_token: str) -> None:
        with self._lock:
            self._require(thread_id, authority_token)
            # revoke outstanding exports from this thread
            for ex in self._exports.values():
                if ex.from_thread == thread_id:
                    ex.revoked = True
            del self._threads[thread_id]

    def write(self, thread_id: str, authority_token: str, key: str, value: object) -> None:
        with self._lock:
            ctx = self._require(thread_id, authority_token)
            ctx.state[key] = value

    def read(self, thread_id: str, authority_token: str, key: str) -> object:
        with self._lock:
            ctx = self._require(thread_id, authority_token)
            return ctx.state.get(key)

    def export(
        self,
        thread_id: str,
        authority_token: str,
        key: str,
        *,
        now: float | None = None,
        ttl_s: float | None = None,
        single_use: bool = False,
    ) -> str:
        t = time.time() if now is None else now
        ttl = self._default_ttl if ttl_s is None else ttl_s
        if ttl <= 0:
            raise ValueError("ttl_s must be positive")
        with self._lock:
            ctx = self._require(thread_id, authority_token)
            if key not in ctx.state:
                raise KeyError("MISSING_KEY")
            export_id = digest({"t": thread_id, "k": key, "v": ctx.state[key], "ts": t})[:16]
            # uniqueness under collision: append counter
            base = export_id
            n = 0
            while export_id in self._exports:
                n += 1
                export_id = digest({"base": base, "n": n})[:16]
            self._exports[export_id] = ExportGrant(
                export_id=export_id,
                from_thread=thread_id,
                key=key,
                value=ctx.state[key],
                not_after=t + ttl,
                single_use=single_use,
            )
            return export_id

    def import_export(
        self,
        thread_id: str,
        authority_token: str,
        export_id: str,
        as_key: str,
        *,
        now: float | None = None,
    ) -> None:
        t = time.time() if now is None else now
        with self._lock:
            ctx = self._require(thread_id, authority_token)
            ex = self._exports.get(export_id)
            if ex is None:
                raise KeyError("UNKNOWN_EXPORT")
            if ex.revoked:
                raise PermissionError("EXPORT_REVOKED")
            if t > ex.not_after:
                raise PermissionError("EXPORT_EXPIRED")
            if ex.consumed and ex.single_use:
                raise PermissionError("EXPORT_CONSUMED")
            if ex.from_thread == thread_id:
                raise ValueError("SELF_IMPORT_USELESS")
            if ex.from_thread not in self._threads:
                raise PermissionError("SOURCE_THREAD_CLOSED")
            ctx.state[as_key] = ex.value
            if ex.single_use:
                ex.consumed = True

    def revoke_export(self, thread_id: str, authority_token: str, export_id: str) -> None:
        with self._lock:
            self._require(thread_id, authority_token)
            ex = self._exports.get(export_id)
            if ex is None:
                raise KeyError("UNKNOWN_EXPORT")
            if ex.from_thread != thread_id:
                raise PermissionError("NOT_OWNER")
            ex.revoked = True

    def _require(self, thread_id: str, authority_token: str) -> ThreadContext:
        ctx = self._threads.get(thread_id)
        if ctx is None:
            raise KeyError("UNKNOWN_THREAD")
        if ctx.authority_token != authority_token:
            raise PermissionError("BAD_AUTHORITY")
        return ctx


def run(example_input: dict) -> dict:
    iso = MissionThreadIsolator(default_export_ttl_s=60.0)
    iso.open("m1", "tok1", now=0.0)
    iso.open("m2", "tok2", now=0.0)
    secret = example_input.get("secret", 1)
    iso.write("m1", "tok1", "secret", secret)
    leaked = iso.read("m2", "tok2", "secret") == secret
    eid = iso.export("m1", "tok1", "secret", now=1.0, single_use=True)
    iso.import_export("m2", "tok2", eid, "imported", now=2.0)
    return {
        "leaked_direct": leaked,
        "imported": iso.read("m2", "tok2", "imported"),
        "export_id": eid,
    }
