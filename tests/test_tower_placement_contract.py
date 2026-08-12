from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEMENT = json.loads(
    (ROOT / "machine" / "tower-placement.json").read_text(encoding="utf-8")
)
STATE = json.loads(
    (ROOT / "machine" / "excellence-state.json").read_text(encoding="utf-8")
)

CURSOR = (
    "next:destination_bound_attenuating_exports_typed_schemas_content_addressed_"
    "provenance_tamper_evident_transfer_audit"
)


def test_placement_binds_exact_current_evolution_cursor_without_rewriting_state():
    assert PLACEMENT["schema"] == "glaciereq.tower-placement.v1"
    assert PLACEMENT["repository"] == STATE["repository"]
    assert STATE["principal_state"] == "EVOLVING"
    assert STATE["evolution_cursor"] == CURSOR
    assert PLACEMENT["evolution_cursor"] == CURSOR


def test_tower_authority_binds_semantic_catalog_and_quality_surfaces():
    authority = PLACEMENT["tower_authority"]
    assert authority["repository"] == "GlacierEQ/the-tower-of-babel"
    assert authority["contract_path"] == "governance/evolution-placement-contract.v1.json"
    assert authority["registry_path"] == "registry/tower.yml"
    assert authority["technology_catalog_path"] == "generated/smithery.registry.json"
    assert authority["quality_contract_path"] == "QUALITY_CONTRACT.md"
    for key in (
        "commit_sha",
        "contract_blob_sha",
        "registry_blob_sha",
        "technology_catalog_blob_sha",
        "quality_contract_blob_sha",
    ):
        assert len(authority[key]) == 40


def test_language_diversity_has_distinct_architectural_ownership():
    assert PLACEMENT["current_languages"] == ["python"]
    boundaries = {row["candidate_technology"]: row for row in PLACEMENT["boundaries"]}
    assert set(boundaries) == {"protobuf", "rust"}

    protobuf = boundaries["protobuf"]
    assert protobuf["decision"] == "ADD"
    assert protobuf["proof_tier"] == "B"
    assert protobuf["parity_required"] is True
    assert "language-neutral" in protobuf["responsibility"]
    assert "ExportEnvelope" in protobuf["interface_contract"]

    rust = boundaries["rust"]
    assert rust["decision"] == "EXPERIMENT"
    assert rust["proof_tier"] == "B"
    assert rust["parity_required"] is True
    assert "provenance" in rust["responsibility"]
    assert "cannot mutate thread state" in rust["interface_contract"]


def test_rust_experiment_does_not_displace_authoritative_python_before_proof():
    assert PLACEMENT["decision"] == "EXPERIMENT"
    nonclaims = " ".join(PLACEMENT["nonclaims"]).lower()
    assert "python implementation remains authoritative" in nonclaims
    assert "rust is an experiment" in nonclaims
    assert "language count" in PLACEMENT["diversity_value"].lower()
