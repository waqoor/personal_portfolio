from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_github_funding_configuration_uses_the_portfolio_owner() -> None:
    funding = REPOSITORY_ROOT / ".github" / "FUNDING.yml"

    assert funding.read_text(encoding="utf-8") == "github: yazeedhasan97\n"
