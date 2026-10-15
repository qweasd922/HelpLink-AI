from services import notify_service as n

R = {"title": "Bin full", "category": "Cleaning", "location_name": "Canteen", "description": "x"}


class Fake:
    def __init__(self, emails=(), demo=False, boom=False):
        self.emails, self.is_demo, self.boom = list(emails), demo, boom

    def fixer_emails(self, c):
        if self.boom:
            raise RuntimeError("db down")
        return self.emails


def test_no_fixers():
    assert "No fixers" in n.notify_fixers(R, Fake())


def test_demo_is_labelled_simulated():
    assert "SIMULATED" in n.notify_fixers(R, Fake(["a@x.com"], demo=True))


def test_lookup_failure_does_not_raise():
    assert "could not be looked up" in n.notify_fixers(R, Fake(boom=True))


def test_smtp_not_configured(monkeypatch):
    monkeypatch.setattr(n, "smtp_ready", lambda: False)
    assert "isn't configured" in n.notify_fixers(R, Fake(["a@x.com"]))


def test_sends_to_matching_fixers(monkeypatch):
    sent = []
    monkeypatch.setattr(n, "smtp_ready", lambda: True)
    monkeypatch.setattr(n, "send_email", lambda r, to: sent.append(to))
    assert "notified" in n.notify_fixers(R, Fake(["a@x.com", "b@x.com"]))
    assert sent == [["a@x.com", "b@x.com"]]


def test_send_failure_does_not_raise(monkeypatch):
    def fail(r, to): raise OSError("smtp down")
    monkeypatch.setattr(n, "smtp_ready", lambda: True)
    monkeypatch.setattr(n, "send_email", fail)
    assert "failed" in n.notify_fixers(R, Fake(["a@x.com"]))
