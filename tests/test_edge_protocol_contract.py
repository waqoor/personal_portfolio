from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_local_default_serves_http_on_port_18444() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert '"${HTTP_PORT:-18444}:80"' in compose
    assert "SITE_ADDRESS: ${SITE_ADDRESS:-http://localhost}" in compose


def test_production_tls_edge_redirects_plain_http_on_port_18444() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    caddyfile = (ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    production_environment = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert '"${HTTPS_PORT:-18445}:443"' in compose
    assert "SITE_ADDRESS=https://portfolio.example.com" in production_environment
    assert "HTTPS_PORT=18444" in production_environment
    assert "PORTFOLIO_COOKIE_SECURE=true" in production_environment
    assert "upgrade-insecure-requests" in production_environment
    assert "servers :443" in caddyfile
    assert "@secure protocol https" in caddyfile
    assert 'header @secure Strict-Transport-Security "max-age=63072000;' in caddyfile

    listener_wrappers = caddyfile.split("listener_wrappers", maxsplit=1)[1]
    http_redirect_position = listener_wrappers.index("http_redirect")
    tls_position = listener_wrappers.index("tls")

    assert http_redirect_position < tls_position
