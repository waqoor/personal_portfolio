from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CROSS_SERVICE_MODULES = {"contracts", "schemas"}


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def test_services_cross_only_public_contract_boundaries() -> None:
    violations: list[str] = []
    for path in _python_files(ROOT / "services"):
        owner = path.relative_to(ROOT / "services").parts[0]
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                parts = node.module.split(".")
                if len(parts) < 2 or parts[0] != "services" or parts[1] == owner:
                    continue
                boundary = parts[2] if len(parts) > 2 else ""
                if boundary not in PUBLIC_CROSS_SERVICE_MODULES:
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno} imports private "
                        f"cross-service module {node.module}"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    if len(parts) >= 2 and parts[0] == "services" and parts[1] != owner:
                        violations.append(
                            f"{path.relative_to(ROOT)}:{node.lineno} imports cross-service "
                            f"package {alias.name} without an explicit public boundary"
                        )
    assert violations == []


def test_shared_python_packages_do_not_depend_on_domain_services_or_apps() -> None:
    violations: list[str] = []
    for path in _python_files(ROOT / "packages" / "python"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            line_number = getattr(node, "lineno", 0)
            for module in modules:
                if module == "services" or module.startswith("services."):
                    violations.append(f"{path.relative_to(ROOT)}:{line_number} imports {module}")
                if module == "apps" or module.startswith("apps."):
                    violations.append(f"{path.relative_to(ROOT)}:{line_number} imports {module}")
    assert violations == []


def test_frontend_packages_do_not_import_application_private_modules() -> None:
    violations: list[str] = []
    for path in sorted((ROOT / "packages" / "frontend").rglob("*.ts*")):
        if any(part in {"node_modules", "coverage"} for part in path.parts):
            continue
        source = path.read_text(encoding="utf-8")
        for marker in ('from "@/', "from '@/", 'from "apps/', "from 'apps/"):
            if marker in source:
                violations.append(f"{path.relative_to(ROOT)} imports an application-private path")
                break
    assert violations == []


def test_api_host_does_not_own_private_domain_implementations() -> None:
    """Only explicit dependency wiring may construct repositories/services."""

    approved_wiring = {"main.py", "dependencies.py", "seed.py", "manage.py"}
    violations: list[str] = []
    for path in _python_files(ROOT / "apps" / "api"):
        if path.name in approved_wiring:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            for module in modules:
                parts = module.split(".")
                if (
                    len(parts) >= 3
                    and parts[0] == "services"
                    and parts[2]
                    in {
                        "models",
                        "repository",
                        "service",
                    }
                ):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{getattr(node, 'lineno', 0)} imports "
                        f"private domain module {module}"
                    )
    assert violations == []


def test_frontend_cache_invalidation_has_a_writable_production_route() -> None:
    """The browser mutation hook must reach Next, not the proxied backend API."""

    browser_api = (ROOT / "apps" / "web" / "lib" / "browser-api.ts").read_text(encoding="utf-8")
    route = ROOT / "apps" / "web" / "app" / "admin" / "revalidate-public" / "route.ts"
    legacy_api_route = (
        ROOT / "apps" / "web" / "app" / "api" / "admin" / "revalidate-public" / "route.ts"
    )
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    web_dockerfile = (ROOT / "deploy" / "docker" / "web.Dockerfile").read_text(encoding="utf-8")
    runtime_fallbacks = [
        ROOT / "apps" / "web" / "app" / "not-found.tsx",
        ROOT / "apps" / "web" / "app" / "admin" / "(auth)" / "login" / "page.tsx",
        ROOT / "apps" / "web" / "app" / "resume-unavailable" / "page.tsx",
    ]

    assert 'fetch("/admin/revalidate-public"' in browser_api
    assert route.is_file()
    assert not legacy_api_route.exists()
    assert "/app/apps/web/.next/cache:uid=1000,gid=1000,mode=0750" in compose
    assert compose.count("API_PROXY_TARGET: http://api:8000") == 2
    assert "ARG API_PROXY_TARGET" in web_dockerfile
    assert all(
        'export const dynamic = "force-dynamic"' in path.read_text(encoding="utf-8")
        for path in runtime_fallbacks
    )


def test_production_compose_bind_sources_are_repository_files() -> None:
    """A missing bind source becomes a directory and prevents container startup."""

    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    required_files = {
        "./deploy/Caddyfile:/etc/caddy/Caddyfile:ro": ROOT / "deploy" / "Caddyfile",
    }
    required_directories = {
        "./deploy/scripts:/scripts:ro": ROOT / "deploy" / "scripts",
    }

    for binding, source in required_files.items():
        assert binding in compose
        assert source.is_file()
    for binding, source in required_directories.items():
        assert binding in compose
        assert source.is_dir()
