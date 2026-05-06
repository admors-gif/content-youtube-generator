import api
from fastapi import HTTPException


def test_free_included_credits_are_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CONTENT_FACTORY_FREE_INCLUDED_CREDITS", raising=False)
    monkeypatch.setattr(api, "_ADMIN_EMAILS", set())

    counts = api._credits_remaining({
        "plan": "free",
        "email": "lead@example.com",
        "credits": {"included": 1, "used": 0, "extra": 0},
    })

    assert counts["included"] == 0
    assert counts["remaining"] == 0


def test_free_extra_credits_still_work_when_included_are_disabled(monkeypatch):
    monkeypatch.delenv("CONTENT_FACTORY_FREE_INCLUDED_CREDITS", raising=False)
    monkeypatch.setattr(api, "_ADMIN_EMAILS", set())

    counts = api._credits_remaining({
        "plan": "free",
        "email": "lead@example.com",
        "credits": {"included": 1, "used": 0, "extra": 2},
    })

    assert counts["included"] == 0
    assert counts["extra"] == 2
    assert counts["remaining"] == 2


def test_admin_email_can_keep_included_credits(monkeypatch):
    monkeypatch.delenv("CONTENT_FACTORY_FREE_INCLUDED_CREDITS", raising=False)
    monkeypatch.setattr(api, "_ADMIN_EMAILS", {"owner@example.com"})

    counts = api._credits_remaining({
        "plan": "free",
        "email": "owner@example.com",
        "credits": {"included": 1, "used": 0, "extra": 0},
    })

    assert counts["included"] == 1
    assert counts["remaining"] == 1


def test_balance_after_delta_tracks_remaining():
    before = {"included": 0, "extra": 2, "used": 0, "total": 2, "remaining": 2}

    after_consume = api._balance_after_delta(before, used_delta=1)
    after_refund = api._balance_after_delta(after_consume, used_delta=-1)
    after_grant = api._balance_after_delta(before, extra_delta=3)

    assert after_consume["used"] == 1
    assert after_consume["remaining"] == 1
    assert after_refund["used"] == 0
    assert after_refund["remaining"] == 2
    assert after_grant["extra"] == 5
    assert after_grant["remaining"] == 5


def test_credit_ledger_payload_contains_audit_fields():
    class FirestoreStub:
        SERVER_TIMESTAMP = "SERVER_TIMESTAMP"

    payload = api._credit_ledger_payload(
        uid="u1",
        entry_type="grant",
        amount=2,
        reason="admin_credit_grant",
        actor="admors@gmail.com",
        firestore=FirestoreStub,
        balance_before={"remaining": 0},
        balance_after={"remaining": 2},
    )

    assert payload["uid"] == "u1"
    assert payload["type"] == "grant"
    assert payload["amount"] == 2
    assert payload["actor"] == "admors@gmail.com"
    assert payload["createdAt"] == "SERVER_TIMESTAMP"
    assert payload["balanceAfter"]["remaining"] == 2


def test_admin_grant_increment_covers_disabled_free_credit_debt():
    counts = {"included": 0, "extra": 0, "used": 1, "total": 0, "remaining": 0}
    increment = api._extra_increment_for_grant(counts, 1)
    after = api._balance_after_delta(counts, extra_delta=increment)

    assert increment == 2
    assert after["remaining"] == 1


def test_long_meditation_payload_accepts_duration_profile():
    payload = api._validate_project_payload({
        "title": "Dormir profundamente",
        "agentId": "agent_meditacion_larga",
        "agentFile": "agent_meditacion_larga.md",
        "durationProfile": "3h",
    })

    assert payload["generation_options"]["duration_profile"] == "180m"


def test_wellness_payload_accepts_private_personalization():
    payload = api._validate_project_payload({
        "title": "Autoconfianza profunda",
        "agentId": "agent_autohipnosis",
        "agentFile": "agent_autohipnosis.md",
        "personalization": {
            "preferredName": "  Tomas  ",
            "purpose": "Dormir con calma y confiar mas en mis decisiones.",
            "anchorPhrase": "Estoy a salvo en mi propio ritmo",
        },
    })

    personalization = payload["generation_options"]["personalization"]

    assert personalization["enabled"] is True
    assert personalization["preferred_name"] == "Tomas"
    assert personalization["purpose"].startswith("Dormir con calma")
    assert personalization["anchor_phrase"] == "Estoy a salvo en mi propio ritmo"
    assert payload["personalization"] == personalization


def test_documentary_payload_ignores_personalization_fields():
    payload = api._validate_project_payload({
        "title": "Historia de Roma",
        "agentId": "agent_historico",
        "agentFile": "agent_historico.md",
        "personalization": {"preferredName": "Tomas"},
    })

    assert payload["personalization"] == {}
    assert "personalization" not in payload["generation_options"]


def test_wellness_payload_rejects_overlong_personalization():
    try:
        api._validate_project_payload({
            "title": "Meditacion para dormir",
            "agentId": "agent_meditacion_larga",
            "agentFile": "agent_meditacion_larga.md",
            "personalization": {"preferredName": "x" * 41},
        })
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "personalization.preferredName too long"
    else:
        raise AssertionError("overlong personalization should be rejected")


def test_long_meditation_payload_rejects_invalid_duration_profile():
    try:
        api._validate_project_payload({
            "title": "Dormir profundamente",
            "agentId": "agent_meditacion_larga",
            "agentFile": "agent_meditacion_larga.md",
            "durationProfile": "12h",
        })
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "invalid durationProfile"
    else:
        raise AssertionError("invalid duration profile should be rejected")
