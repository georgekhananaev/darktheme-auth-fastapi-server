"""Input validation for certbot calls in CertificateManager."""
import asyncio

import pytest

from modules import certificate_manager as cm


class _Done:
    returncode = 1
    stderr = "stopped by test"


@pytest.fixture
def certbot_calls(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _Done()

    monkeypatch.setattr(cm.subprocess, "run", fake_run)
    monkeypatch.setattr(cm.CertificateManager, "_challenge_type", "dns-cloudflare", raising=False)
    return calls


def issue(**kwargs):
    return asyncio.run(cm.CertificateManager.issue_certificate(**kwargs))


@pytest.mark.parametrize("domain", [
    "--config-dir=/tmp/evil",
    "example.com --deploy-hook=touch /tmp/pwned",
    "../../etc",
    "exa mple.com",
    "-example.com",
])
def test_rejects_domains_that_could_become_options_or_paths(certbot_calls, domain):
    result = issue(domains=[domain], email="admin@example.com")
    assert result["success"] is False
    assert "Invalid domain" in result["message"]
    assert certbot_calls == []


def test_rejects_invalid_email(certbot_calls):
    result = issue(domains=["example.com"], email="--agree-tos")
    assert result["success"] is False
    assert certbot_calls == []


def test_passes_each_value_as_its_own_argument(certbot_calls):
    issue(domains=["example.com", "*.example.com"], email="admin@example.com")
    cmd = certbot_calls[0]
    assert cmd[cmd.index("--email") + 1] == "admin@example.com"
    assert [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "-d"] == ["example.com", "*.example.com"]


def test_copy_refuses_paths_outside_letsencrypt(tmp_path, monkeypatch):
    monkeypatch.setattr(cm.CertificateManager, "_cert_dir", str(tmp_path), raising=False)
    assert asyncio.run(cm.CertificateManager._copy_certbot_certificates("../../etc")) is False
