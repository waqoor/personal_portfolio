from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict[str, object]:
    return json.loads((ROOT / "yazeed.portfolio.manifest.json").read_text(encoding="utf-8"))


def test_yazeed_manifest_matches_public_identity_and_navigation_contract() -> None:
    manifest = _manifest()
    profile = manifest["identity"]["profiles"][0]["payload"]
    navigation = manifest["content"]["navigation"]
    header = [
        (item["payload"]["label"], item["payload"]["href"])
        for item in navigation
        if item["payload"].get("location", "header") == "header"
    ]

    assert profile["headline"] == (
        "AI & Data Technical Leader | Enterprise AI/ML, Data Platforms, MLOps, Strategy & Delivery"
    )
    assert "9+ years" in profile["short_bio"]
    assert "seven-member" in profile["short_bio"]
    assert "Leadership philosophy / approach" in profile["long_bio"]
    assert header == [
        ("Work", "/work"),
        ("Projects", "/projects"),
        ("Achievements", "/achievements"),
        ("Sponsor", "/sponsor"),
    ]
    assert all(label not in {"About", "Contact"} for label, _ in header)


def test_yazeed_homepage_consolidates_profile_content_without_placeholders() -> None:
    manifest = _manifest()
    sections = manifest["content"]["homepage_sections"]
    section_types = [item["payload"]["section_type"] for item in sections]
    serialized = json.dumps(manifest).lower()

    assert section_types[0:2] == ["hero", "editorial"]
    assert {"skills", "experience", "education", "resume"} <= set(section_types)
    assert "will be added" not in serialized
    assert "will expand" not in serialized
    assert "to be added" not in serialized


def test_yazeed_manifest_keeps_the_reviewed_resume_linkedin_and_supported_metrics() -> None:
    manifest = _manifest()
    identity = manifest["identity"]
    profile = identity["profiles"][0]["payload"]
    linkedin = next(
        link["payload"]
        for link in identity["social_links"]
        if link["payload"]["platform"] == "LinkedIn"
    )
    portrait = identity["portraits"][0]
    resume = identity["resume_versions"][0]

    assert linkedin["url"] == "https://www.linkedin.com/in/yazeed-hasan-ba02101b6"
    assert portrait["file"] == "portfolio_image.png"
    assert portrait["make_primary"] is True
    assert resume["file"] == "YazeedHasanResume.pdf"
    assert resume["download_name"] == "Yazeed-Hasan-Resume.pdf"
    assert resume["make_current"] is True
    assert all(metric in profile["long_bio"] for metric in ("25%", "20%", "40%", "60%"))
