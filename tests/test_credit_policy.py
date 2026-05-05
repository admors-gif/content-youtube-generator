import api


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
