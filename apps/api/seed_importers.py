"""Bounded input adapters that produce canonical, draft-only seed manifests."""

from __future__ import annotations

import calendar
import csv
import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, cast
from urllib.parse import urlsplit

_MAX_JSON_BYTES = 5 * 1024 * 1024
_MAX_LINKEDIN_ARCHIVE_BYTES = 20 * 1024 * 1024
_MAX_LINKEDIN_MEMBERS = 64
_MAX_LINKEDIN_MEMBER_BYTES = 2 * 1024 * 1024
_MAX_LINKEDIN_TOTAL_BYTES = 10 * 1024 * 1024
_MAX_CSV_ROWS = 1_000
_MAX_CELL_CHARS = 20_000
_MAX_RECORDS_PER_GROUP = 500
_SLUG_PARTS = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True, slots=True)
class SeedImportResult:
    manifest: dict[str, Any]
    warnings: tuple[str, ...]


def import_json_resume(path: Path, *, manifest_directory: Path) -> SeedImportResult:
    raw = _read_bounded_file(path, _MAX_JSON_BYTES, "JSON Resume")
    parsed = _load_unique_json(raw)
    if not isinstance(parsed, dict):
        raise ValueError("JSON Resume input must be an object.")
    document = cast(dict[str, Any], parsed)
    warnings: list[str] = []
    profile_key = "resume.profile.primary"

    basics = _mapping(document.get("basics"), "basics")
    name = _required_text(basics.get("name"), "basics.name", 160)
    headline = _optional_text(basics.get("label"), "basics.label", 240) or (
        "Imported profile awaiting a reviewed headline"
    )
    summary = _optional_text(basics.get("summary"), "basics.summary", 20_000)
    if not summary:
        summary = "Draft JSON Resume import; add a reviewed biography before publication."
        warnings.append("basics.summary was absent; a non-public review placeholder was added.")
    location = _json_resume_location(basics.get("location"))
    email = _optional_text(basics.get("email"), "basics.email", 320)
    website = _optional_https_url(basics.get("url"), "basics.url")
    profile_payload: dict[str, Any] = {
        "full_name": name,
        "headline": headline,
        "short_bio": summary[:2_000],
        "long_bio": summary if len(summary) > 2_000 else None,
        "public_location": location,
        "public_email": email,
        "primary_cta_label": "Website" if website else None,
        "primary_cta_url": website,
        "is_primary": True,
        **_draft_publication(),
    }

    social_links: list[dict[str, Any]] = []
    for index, network in enumerate(_list(basics.get("profiles"), "basics.profiles")):
        item = _mapping(network, f"basics.profiles[{index}]")
        platform = _required_text(item.get("network"), f"basics.profiles[{index}].network", 80)
        url = _required_https_url(item.get("url"), f"basics.profiles[{index}].url")
        username = _optional_text(item.get("username"), f"basics.profiles[{index}].username", 160)
        social_links.append(
            {
                "seed_key": _seed_key("resume.social", platform, index),
                "profile_seed_key": profile_key,
                "payload": {
                    "platform": platform,
                    "label": platform,
                    "url": url,
                    "handle": username,
                    "sort_order": index,
                    "is_visible": True,
                },
            }
        )

    categories: list[dict[str, Any]] = []
    skills: list[dict[str, Any]] = []
    skill_keys: dict[str, str] = {}

    def ensure_skill(value: str, *, group: str | None = None) -> str:
        normalized = value.casefold()
        existing = skill_keys.get(normalized)
        if existing:
            return existing
        if len(skills) >= _MAX_RECORDS_PER_GROUP:
            raise ValueError("JSON Resume contains too many distinct skills.")
        key = _seed_key("resume.skill", value, len(skills))
        skill_keys[normalized] = key
        skills.append(
            {
                "seed_key": key,
                "category_seed_key": _seed_key("resume.category", group, 0) if group else None,
                "payload": {
                    "name": value,
                    "slug": _slug(value, fallback=f"skill-{len(skills) + 1}"),
                    "description": None,
                    "proficiency_label": None,
                    "years_experience": None,
                    "sort_order": len(skills),
                    **_draft_publication(),
                },
            }
        )
        return key

    category_names: set[str] = set()
    for index, raw_skill in enumerate(_list(document.get("skills"), "skills")):
        item = _mapping(raw_skill, f"skills[{index}]")
        group = _required_text(item.get("name"), f"skills[{index}].name", 120)
        keywords = _text_list(item.get("keywords"), f"skills[{index}].keywords", 120)
        if keywords:
            category_key = _seed_key("resume.category", group, 0)
            if category_key not in category_names:
                category_names.add(category_key)
                categories.append(
                    {
                        "seed_key": category_key,
                        "payload": {
                            "name": group,
                            "slug": _slug(group, fallback=f"skill-group-{index + 1}"),
                            "description": f"Imported JSON Resume skill group: {group}.",
                            "sort_order": len(categories),
                            **_draft_publication(),
                        },
                    }
                )
            for keyword in keywords:
                ensure_skill(keyword, group=group)
        else:
            ensure_skill(group)

    experiences: list[dict[str, Any]] = []
    work_items = [
        *(("work", item) for item in _list(document.get("work"), "work")),
        *(("volunteer", item) for item in _list(document.get("volunteer"), "volunteer")),
    ]
    for index, (kind, raw_work) in enumerate(work_items):
        item = _mapping(raw_work, f"{kind}[{index}]")
        organization_field = "organization" if kind == "volunteer" else "name"
        organization = _required_text(
            item.get(organization_field), f"{kind}[{index}].{organization_field}", 200
        )
        role = _required_text(item.get("position"), f"{kind}[{index}].position", 200)
        started = _parse_date(item.get("startDate"), f"{kind}[{index}].startDate")
        if started is None:
            warnings.append(f"{kind}[{index}] was skipped because startDate is required.")
            continue
        summary_value = _optional_text(item.get("summary"), f"{kind}[{index}].summary", 20_000)
        highlights = _text_list(item.get("highlights"), f"{kind}[{index}].highlights", 100)
        summary_value = summary_value or (
            highlights[0] if highlights else f"{role} at {organization}"
        )
        experiences.append(
            {
                "seed_key": _seed_key("resume.experience", f"{organization}-{role}", index),
                "skill_seed_keys": [],
                "sector_seed_keys": [],
                "project_seed_keys": [],
                "payload": {
                    "organization": organization,
                    "role": role,
                    "location": _optional_text(
                        item.get("location"), f"{kind}[{index}].location", 160
                    ),
                    "employment_type": "Volunteer" if kind == "volunteer" else None,
                    "start_date": started,
                    "end_date": _parse_date(
                        item.get("endDate"), f"{kind}[{index}].endDate", end=True
                    ),
                    "summary": summary_value,
                    "achievements": highlights,
                    "sort_order": index,
                    **_draft_publication(),
                },
            }
        )

    education: list[dict[str, Any]] = []
    for index, raw_education in enumerate(_list(document.get("education"), "education")):
        item = _mapping(raw_education, f"education[{index}]")
        institution = _required_text(
            item.get("institution"), f"education[{index}].institution", 200
        )
        credential = (
            _optional_text(item.get("studyType"), f"education[{index}].studyType", 200)
            or "Education record"
        )
        courses = _text_list(item.get("courses"), f"education[{index}].courses", 100)
        education.append(
            {
                "seed_key": _seed_key("resume.education", f"{institution}-{credential}", index),
                "payload": {
                    "institution": institution,
                    "credential": credential,
                    "field_of_study": _optional_text(
                        item.get("area"), f"education[{index}].area", 200
                    ),
                    "start_date": _parse_date(
                        item.get("startDate"), f"education[{index}].startDate"
                    ),
                    "end_date": _parse_date(
                        item.get("endDate"), f"education[{index}].endDate", end=True
                    ),
                    "summary": None,
                    "achievements": courses,
                    "sort_order": index,
                    **_draft_publication(),
                },
            }
        )

    certifications: list[dict[str, Any]] = []
    certificate_sources = (
        ("certificates", document.get("certificates")),
        ("awards", document.get("awards")),
    )
    for group_name, raw_group in certificate_sources:
        for index, raw_certificate in enumerate(_list(raw_group, group_name)):
            item = _mapping(raw_certificate, f"{group_name}[{index}]")
            name_field = "title" if group_name == "awards" else "name"
            issuer_field = "awarder" if group_name == "awards" else "issuer"
            certificate_name = _required_text(
                item.get(name_field), f"{group_name}[{index}].{name_field}", 240
            )
            issuer = _optional_text(
                item.get(issuer_field),
                f"{group_name}[{index}].{issuer_field}",
                200,
            )
            if not issuer:
                warnings.append(f"{group_name}[{index}] was skipped because its issuer is absent.")
                continue
            certifications.append(
                {
                    "seed_key": _seed_key(
                        "resume.certification", f"{issuer}-{certificate_name}", index
                    ),
                    "payload": {
                        "name": certificate_name,
                        "issuer": issuer,
                        "credential_url": _optional_https_url(
                            item.get("url"), f"{group_name}[{index}].url"
                        ),
                        "issued_on": _parse_date(item.get("date"), f"{group_name}[{index}].date"),
                        "description": _optional_text(
                            item.get("summary"), f"{group_name}[{index}].summary", 10_000
                        ),
                        "sort_order": len(certifications),
                        **_draft_publication(),
                    },
                }
            )

    projects: list[dict[str, Any]] = []
    for index, raw_project in enumerate(_list(document.get("projects"), "projects")):
        item = _mapping(raw_project, f"projects[{index}]")
        title = _required_text(item.get("name"), f"projects[{index}].name", 200)
        description = _optional_text(
            item.get("description"), f"projects[{index}].description", 50_000
        )
        highlights = _text_list(item.get("highlights"), f"projects[{index}].highlights", 200)
        keywords = _text_list(item.get("keywords"), f"projects[{index}].keywords", 200)
        project_skill_keys = [ensure_skill(keyword) for keyword in keywords]
        project_url = _optional_https_url(item.get("url"), f"projects[{index}].url")
        roles = _text_list(item.get("roles"), f"projects[{index}].roles", 20)
        projects.append(
            {
                "seed_key": _seed_key("resume.project", title, index),
                "category_seed_key": None,
                "skill_seed_keys": project_skill_keys,
                "sector_seed_keys": [],
                "payload": {
                    "title": title,
                    "slug": _slug(title, fallback=f"project-{index + 1}"),
                    "summary": (description or title)[:2_000],
                    "description": description,
                    "role": ", ".join(roles)[:200] or None,
                    "start_date": _parse_date(
                        item.get("startDate"), f"projects[{index}].startDate"
                    ),
                    "end_date": _parse_date(
                        item.get("endDate"), f"projects[{index}].endDate", end=True
                    ),
                    "outcomes": highlights,
                    "live_url": project_url,
                    "is_open_source": False,
                    "repository_metadata_refresh_enabled": False,
                    **_draft_publication(),
                },
            }
        )

    testimonials: list[dict[str, Any]] = []
    for index, raw_reference in enumerate(_list(document.get("references"), "references")):
        item = _mapping(raw_reference, f"references[{index}]")
        attribution = _required_text(item.get("name"), f"references[{index}].name", 160)
        quote = _required_text(item.get("reference"), f"references[{index}].reference", 20_000)
        testimonials.append(
            {
                "seed_key": _seed_key("resume.testimonial", attribution, index),
                "project_seed_key": None,
                "experience_seed_key": None,
                "payload": {
                    "subject_label": "Imported reference",
                    "quote": quote,
                    "attribution_name": attribution,
                    "evidence": None,
                    "sort_order": index,
                    **_draft_publication(),
                },
            }
        )

    portraits, resume_versions = _json_resume_assets(
        document,
        basics,
        path=path,
        manifest_directory=manifest_directory,
        profile_key=profile_key,
        full_name=name,
        warnings=warnings,
    )
    ignored_groups = [
        key for key in ("publications", "languages", "interests") if document.get(key)
    ]
    if ignored_groups:
        warnings.append(
            "No canonical destination exists for these JSON Resume groups: "
            + ", ".join(ignored_groups)
            + ". They were not imported."
        )

    manifest = _manifest(
        source="resume",
        importer="json_resume",
        input_path=path,
        raw_digest=hashlib.sha256(raw).hexdigest(),
        warnings=warnings,
        identity={
            "profiles": [{"seed_key": profile_key, "payload": profile_payload}],
            "social_links": social_links,
            "portraits": portraits,
            "resume_versions": resume_versions,
        },
        portfolio={
            "categories": categories,
            "skills": skills,
            "projects": projects,
            "experiences": experiences,
            "education": education,
            "certifications": certifications,
            "testimonials": testimonials,
        },
    )
    return SeedImportResult(manifest=manifest, warnings=tuple(warnings))


def import_linkedin_export(path: Path) -> SeedImportResult:
    raw = _read_bounded_file(path, _MAX_LINKEDIN_ARCHIVE_BYTES, "LinkedIn export")
    tables = _read_linkedin_tables(raw)
    warnings: list[str] = []
    profile_rows = tables.get("profile.csv", [])
    if len(profile_rows) != 1:
        raise ValueError("LinkedIn export must contain exactly one row in Profile.csv.")
    profile = profile_rows[0]
    first_name = _csv_value(profile, "First Name", max_length=80)
    last_name = _csv_value(profile, "Last Name", max_length=80)
    full_name = " ".join(part for part in (first_name, last_name) if part)
    if not full_name:
        raise ValueError("LinkedIn Profile.csv does not contain a name.")
    headline = _csv_value(profile, "Headline", max_length=240)
    if not headline:
        headline = "Imported profile awaiting a reviewed headline"
        warnings.append("LinkedIn headline was absent; a non-public review placeholder was added.")
    summary = _csv_value(profile, "Summary", max_length=20_000)
    if not summary:
        summary = "Draft LinkedIn import; add a reviewed biography before publication."
        warnings.append("LinkedIn summary was absent; a non-public review placeholder was added.")
    profile_key = "linkedin.profile.primary"
    profile_payload = {
        "full_name": full_name,
        "headline": headline,
        "short_bio": summary[:2_000],
        "long_bio": summary if len(summary) > 2_000 else None,
        "public_location": _csv_value(profile, "Geo Location", "Address", max_length=160),
        "is_primary": True,
        **_draft_publication(),
    }

    skills: list[dict[str, Any]] = []
    for index, row in enumerate(tables.get("skills.csv", [])):
        name = _csv_value(row, "Name", max_length=120)
        if not name:
            continue
        skills.append(
            {
                "seed_key": _seed_key("linkedin.skill", name, index),
                "category_seed_key": None,
                "payload": {
                    "name": name,
                    "slug": _slug(name, fallback=f"skill-{index + 1}"),
                    "sort_order": index,
                    **_draft_publication(),
                },
            }
        )

    experiences: list[dict[str, Any]] = []
    for index, row in enumerate(tables.get("positions.csv", [])):
        organization = _csv_value(row, "Company Name", max_length=200)
        role = _csv_value(row, "Title", max_length=200)
        started = _parse_date(_csv_value(row, "Started On"), f"Positions.csv[{index}].Started On")
        if not (organization and role and started):
            warnings.append(
                f"Positions.csv row {index + 1} was skipped because company, title, "
                "or start date is absent."
            )
            continue
        description = _csv_value(row, "Description", max_length=20_000) or (
            f"{role} at {organization}"
        )
        experiences.append(
            {
                "seed_key": _seed_key("linkedin.experience", f"{organization}-{role}", index),
                "skill_seed_keys": [],
                "sector_seed_keys": [],
                "project_seed_keys": [],
                "payload": {
                    "organization": organization,
                    "role": role,
                    "location": _csv_value(row, "Location", max_length=160),
                    "start_date": started,
                    "end_date": _parse_date(
                        _csv_value(row, "Finished On"),
                        f"Positions.csv[{index}].Finished On",
                        end=True,
                    ),
                    "summary": description,
                    "achievements": [],
                    "sort_order": index,
                    **_draft_publication(),
                },
            }
        )

    education: list[dict[str, Any]] = []
    for index, row in enumerate(tables.get("education.csv", [])):
        institution = _csv_value(row, "School Name", max_length=200)
        if not institution:
            continue
        credential = _csv_value(row, "Degree Name", max_length=200) or "Education record"
        activities = _csv_value(row, "Activities", max_length=5_000)
        education.append(
            {
                "seed_key": _seed_key("linkedin.education", f"{institution}-{credential}", index),
                "payload": {
                    "institution": institution,
                    "credential": credential,
                    "field_of_study": _csv_value(row, "Field Of Study", max_length=200),
                    "start_date": _parse_date(
                        _csv_value(row, "Start Date"), f"Education.csv[{index}].Start Date"
                    ),
                    "end_date": _parse_date(
                        _csv_value(row, "End Date"),
                        f"Education.csv[{index}].End Date",
                        end=True,
                    ),
                    "summary": _csv_value(row, "Notes", max_length=20_000),
                    "achievements": [activities] if activities else [],
                    "sort_order": index,
                    **_draft_publication(),
                },
            }
        )

    certifications: list[dict[str, Any]] = []
    for index, row in enumerate(tables.get("certifications.csv", [])):
        name = _csv_value(row, "Name", max_length=240)
        issuer = _csv_value(row, "Authority", max_length=200)
        if not (name and issuer):
            warnings.append(
                f"Certifications.csv row {index + 1} was skipped because name or "
                "authority is absent."
            )
            continue
        certifications.append(
            {
                "seed_key": _seed_key("linkedin.certification", f"{issuer}-{name}", index),
                "payload": {
                    "name": name,
                    "issuer": issuer,
                    "credential_id": _csv_value(row, "License Number", max_length=200),
                    "credential_url": _optional_https_url(
                        _csv_value(row, "Url", "URL", max_length=2_048),
                        f"Certifications.csv[{index}].Url",
                    ),
                    "issued_on": _parse_date(
                        _csv_value(row, "Started On"),
                        f"Certifications.csv[{index}].Started On",
                    ),
                    "expires_on": _parse_date(
                        _csv_value(row, "Finished On"),
                        f"Certifications.csv[{index}].Finished On",
                        end=True,
                    ),
                    "sort_order": index,
                    **_draft_publication(),
                },
            }
        )

    projects: list[dict[str, Any]] = []
    for index, row in enumerate(tables.get("projects.csv", [])):
        title = _csv_value(row, "Title", "Name", max_length=200)
        if not title:
            continue
        description = _csv_value(row, "Description", max_length=50_000) or title
        project_url = _optional_https_url(
            _csv_value(row, "Url", "URL", max_length=2_048),
            f"Projects.csv[{index}].Url",
        )
        projects.append(
            {
                "seed_key": _seed_key("linkedin.project", title, index),
                "category_seed_key": None,
                "skill_seed_keys": [],
                "sector_seed_keys": [],
                "payload": {
                    "title": title,
                    "slug": _slug(title, fallback=f"project-{index + 1}"),
                    "summary": (description or title)[:2_000],
                    "description": description,
                    "start_date": _parse_date(
                        _csv_value(row, "Started On"), f"Projects.csv[{index}].Started On"
                    ),
                    "end_date": _parse_date(
                        _csv_value(row, "Finished On"),
                        f"Projects.csv[{index}].Finished On",
                        end=True,
                    ),
                    "live_url": project_url,
                    "is_open_source": False,
                    "repository_metadata_refresh_enabled": False,
                    **_draft_publication(),
                },
            }
        )

    testimonials: list[dict[str, Any]] = []
    recommendation_rows = tables.get("recommendations_received.csv", [])
    for index, row in enumerate(recommendation_rows):
        quote = _csv_value(row, "Text", "Recommendation", max_length=20_000)
        attribution = " ".join(
            part
            for part in (
                _csv_value(row, "First Name", max_length=80),
                _csv_value(row, "Last Name", max_length=80),
            )
            if part
        )
        if not (quote and attribution):
            continue
        testimonials.append(
            {
                "seed_key": _seed_key("linkedin.testimonial", attribution, index),
                "project_seed_key": None,
                "experience_seed_key": None,
                "payload": {
                    "subject_label": "Imported LinkedIn recommendation",
                    "quote": quote,
                    "attribution_name": attribution,
                    "attribution_title": _csv_value(row, "Job Title", max_length=160),
                    "attribution_organization": _csv_value(row, "Company", max_length=200),
                    "evidence": None,
                    "sort_order": index,
                    **_draft_publication(),
                },
            }
        )

    ignored = sorted(
        name
        for name in tables
        if name
        not in {
            "profile.csv",
            "skills.csv",
            "positions.csv",
            "education.csv",
            "certifications.csv",
            "projects.csv",
            "recommendations_received.csv",
        }
    )
    if ignored:
        warnings.append(
            "LinkedIn files without canonical portfolio destinations were ignored: "
            + ", ".join(ignored)
        )
    warnings.append(
        "LinkedIn archive media is not extracted automatically; attach reviewed portrait and "
        "resume files through admin or a contained manifest asset."
    )
    manifest = _manifest(
        source="linkedin",
        importer="linkedin_export",
        input_path=path,
        raw_digest=hashlib.sha256(raw).hexdigest(),
        warnings=warnings,
        identity={
            "profiles": [{"seed_key": profile_key, "payload": profile_payload}],
            "social_links": [],
            "portraits": [],
            "resume_versions": [],
        },
        portfolio={
            "skills": skills,
            "projects": projects,
            "experiences": experiences,
            "education": education,
            "certifications": certifications,
            "testimonials": testimonials,
        },
    )
    return SeedImportResult(manifest=manifest, warnings=tuple(warnings))


def _manifest(
    *,
    source: str,
    importer: str,
    input_path: Path,
    raw_digest: str,
    warnings: list[str],
    identity: dict[str, Any],
    portfolio: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": source,
        "review": {
            "importer": importer,
            "source_filename": input_path.name[:255],
            "source_sha256": raw_digest,
            "publication_policy": "draft_review_required",
            "warnings": warnings[:200],
        },
        "identity": identity,
        "portfolio": portfolio,
        "content": {},
    }


def _draft_publication() -> dict[str, object]:
    return {"status": "draft", "is_visible": True, "noindex": True}


def _read_bounded_file(path: Path, maximum: int, label: str) -> bytes:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"{label} input file does not exist.")
    size = resolved.stat().st_size
    if size <= 0 or size > maximum:
        raise ValueError(f"{label} input must be between 1 byte and {maximum} bytes.")
    return resolved.read_bytes()


def _load_unique_json(raw: bytes) -> Any:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("JSON Resume input is not bounded, valid UTF-8 JSON.") from exc


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object.")
    return cast(dict[str, Any], value)


def _list(value: Any, label: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array.")
    if len(value) > _MAX_RECORDS_PER_GROUP:
        raise ValueError(f"{label} exceeds the {_MAX_RECORDS_PER_GROUP}-record limit.")
    return value


def _required_text(value: Any, label: str, maximum: int) -> str:
    result = _optional_text(value, label, maximum)
    if not result:
        raise ValueError(f"{label} is required.")
    return result


def _optional_text(value: Any, label: str, maximum: int) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    result = value.strip()
    if len(result) > maximum:
        raise ValueError(f"{label} exceeds {maximum} characters.")
    return result or None


def _text_list(value: Any, label: str, maximum_items: int) -> list[str]:
    items = _list(value, label)
    if len(items) > maximum_items:
        raise ValueError(f"{label} exceeds {maximum_items} items.")
    return [_required_text(item, f"{label}[{index}]", 2_000) for index, item in enumerate(items)]


def _json_resume_location(value: Any) -> str | None:
    if value is None:
        return None
    location = _mapping(value, "basics.location")
    parts = [
        _optional_text(location.get(field), f"basics.location.{field}", 80)
        for field in ("city", "region", "countryCode")
    ]
    combined = ", ".join(part for part in parts if part)
    return combined[:160] or None


def _optional_https_url(value: Any, label: str) -> str | None:
    text = _optional_text(value, label, 2_048)
    if text is None:
        return None
    parsed = urlsplit(text)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(f"{label} must be an HTTPS URL without credentials.")
    return text


def _required_https_url(value: Any, label: str) -> str:
    result = _optional_https_url(value, label)
    if result is None:
        raise ValueError(f"{label} is required.")
    return result


def _parse_date(value: Any, label: str, *, end: bool = False) -> str | None:
    text = _optional_text(value, label, 40)
    if text is None:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        pass
    year_match = re.fullmatch(r"(\d{4})", text)
    if year_match:
        year = int(year_match.group(1))
        return date(year, 12 if end else 1, 31 if end else 1).isoformat()
    month_match = re.fullmatch(r"(\d{4})-(\d{2})", text)
    if month_match:
        year, month = (int(part) for part in month_match.groups())
        day = calendar.monthrange(year, month)[1] if end else 1
        return date(year, month, day).isoformat()
    for pattern in ("%b %Y", "%B %Y", "%m/%Y"):
        try:
            parsed = datetime.strptime(text, pattern)
        except ValueError:
            continue
        day = calendar.monthrange(parsed.year, parsed.month)[1] if end else 1
        return date(parsed.year, parsed.month, day).isoformat()
    raise ValueError(f"{label} must be YYYY, YYYY-MM, YYYY-MM-DD, or a named month and year.")


def _slug(value: str, *, fallback: str) -> str:
    slug = _SLUG_PARTS.sub("-", value.casefold()).strip("-")
    slug = slug[:220].rstrip("-")
    return slug or fallback


def _seed_key(prefix: str, value: str | None, index: int) -> str:
    suffix = _slug(value or "record", fallback="record")[:100]
    digest = hashlib.sha256(f"{value or ''}\0{index}".encode()).hexdigest()[:10]
    return f"{prefix}.{suffix}.{digest}"[:160].rstrip(".-_")


def _json_resume_assets(
    document: dict[str, Any],
    basics: dict[str, Any],
    *,
    path: Path,
    manifest_directory: Path,
    profile_key: str,
    full_name: str,
    warnings: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    portraits: list[dict[str, Any]] = []
    resumes: list[dict[str, Any]] = []
    image = _optional_text(basics.get("image"), "basics.image", 500)
    if image:
        local = _contained_manifest_asset(
            image,
            input_directory=path.resolve().parent,
            manifest_directory=manifest_directory,
        )
        if local is None:
            warnings.append(
                "basics.image was not imported because only local files contained by the "
                "manifest directory are accepted."
            )
        else:
            media_type = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
                ".avif": "image/avif",
            }.get(Path(local).suffix.casefold())
            if media_type is None:
                warnings.append(
                    "basics.image used an unsupported image extension and was not imported."
                )
            else:
                portraits.append(
                    {
                        "seed_key": "resume.portrait.primary",
                        "profile_seed_key": profile_key,
                        "file": local,
                        "media_type": media_type,
                        "alt_text": f"Portrait of {full_name}",
                        "sort_order": 0,
                        "make_primary": True,
                    }
                )
    extension = document.get("x-portfolio-resume")
    if extension is not None:
        resume = _mapping(extension, "x-portfolio-resume")
        file_value = _required_text(resume.get("file"), "x-portfolio-resume.file", 500)
        local = _contained_manifest_asset(
            file_value,
            input_directory=path.resolve().parent,
            manifest_directory=manifest_directory,
        )
        if local is None or Path(local).suffix.casefold() != ".pdf":
            raise ValueError(
                "x-portfolio-resume.file must be a PDF contained by the manifest directory."
            )
        resumes.append(
            {
                "seed_key": "resume.document.imported",
                "profile_seed_key": profile_key,
                "file": local,
                "version_label": _optional_text(
                    resume.get("version_label"), "x-portfolio-resume.version_label", 120
                )
                or "Imported resume",
                "effective_date": _parse_date(
                    resume.get("effective_date"), "x-portfolio-resume.effective_date"
                ),
                "download_name": _optional_text(
                    resume.get("download_name"), "x-portfolio-resume.download_name", 255
                )
                or "resume.pdf",
                "status": "draft",
                "make_current": False,
            }
        )
    return portraits, resumes


def _contained_manifest_asset(
    value: str, *, input_directory: Path, manifest_directory: Path
) -> str | None:
    if urlsplit(value).scheme or Path(value).is_absolute():
        return None
    candidate = (input_directory / value).resolve()
    manifest_root = manifest_directory.resolve()
    if not candidate.is_file() or not candidate.is_relative_to(manifest_root):
        return None
    return candidate.relative_to(manifest_root).as_posix()


def _read_linkedin_tables(raw: bytes) -> dict[str, list[dict[str, str | None]]]:
    if not zipfile.is_zipfile(io.BytesIO(raw)):
        raise ValueError("LinkedIn input must be a ZIP data export.")
    tables: dict[str, list[dict[str, str | None]]] = {}
    total_size = 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            if len(members) > _MAX_LINKEDIN_MEMBERS:
                raise ValueError("LinkedIn export contains too many files.")
            for member in members:
                pure_name = PurePosixPath(member.filename.replace("\\", "/"))
                if pure_name.is_absolute() or ".." in pure_name.parts:
                    raise ValueError("LinkedIn export contains an unsafe member path.")
                if member.file_size > _MAX_LINKEDIN_MEMBER_BYTES:
                    raise ValueError("A LinkedIn export member exceeds the size limit.")
                total_size += member.file_size
                if total_size > _MAX_LINKEDIN_TOTAL_BYTES:
                    raise ValueError("LinkedIn export expands beyond the total size limit.")
                if member.compress_size == 0 and member.file_size > 0:
                    raise ValueError("LinkedIn export contains an invalid compressed member.")
                if member.compress_size and member.file_size / member.compress_size > 100:
                    raise ValueError("LinkedIn export contains a suspicious compression ratio.")
                if pure_name.suffix.casefold() != ".csv":
                    continue
                key = pure_name.name.casefold().replace(" ", "_")
                if key in tables:
                    raise ValueError(f"LinkedIn export contains duplicate {pure_name.name} files.")
                tables[key] = _parse_csv(archive.read(member), pure_name.name)
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise ValueError("LinkedIn export is corrupt or encrypted.") from exc
    return tables


def _parse_csv(raw: bytes, label: str) -> list[dict[str, str | None]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not UTF-8 CSV.") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames or any(not field for field in reader.fieldnames):
        raise ValueError(f"{label} has an invalid header.")
    rows: list[dict[str, str | None]] = []
    for index, row in enumerate(reader):
        if index >= _MAX_CSV_ROWS:
            raise ValueError(f"{label} exceeds the {_MAX_CSV_ROWS}-row limit.")
        if None in row:
            raise ValueError(f"{label} row {index + 1} contains unexpected columns.")
        normalized: dict[str, str | None] = {}
        for key, value in row.items():
            if value is not None and len(value) > _MAX_CELL_CHARS:
                raise ValueError(f"{label} row {index + 1} contains an oversized cell.")
            normalized[key.strip()] = value.strip() if value else None
        rows.append(normalized)
    return rows


def _csv_value(
    row: dict[str, str | None], *fields: str, max_length: int = _MAX_CELL_CHARS
) -> str | None:
    for field in fields:
        value = row.get(field)
        if value:
            if len(value) > max_length:
                raise ValueError(f"LinkedIn field {field} exceeds {max_length} characters.")
            return value
    return None
