from __future__ import annotations

from packages.python.clients.database import DatabaseClient
from packages.python.common.models import PublicationStatus
from packages.python.common.policies import PublicationPolicy
from packages.python.common.search import extract_search_terms
from services.content.models import Article
from services.content.repository import ContentRepository
from services.portfolio.models import Project, ProjectNature
from services.portfolio.repository import PortfolioRepository


def test_search_terms_remove_question_noise_and_preserve_order() -> None:
    assert extract_search_terms(
        "What does the Verification project prove about verification?",
        max_terms=3,
    ) == ("verification", "project", "prove")
    assert extract_search_terms("what does it do") == ()
    assert extract_search_terms("What is the portfolio owner's favorite coffee?") == (
        "favorite",
        "coffee",
    )
    assert extract_search_terms("FastAPI C++ PostgreSQL") == ("fastapi", "c++", "postgresql")


async def test_public_repositories_match_natural_language_questions(
    database_client: DatabaseClient,
) -> None:
    project = Project(
        title="Canonical Service Verification",
        slug="canonical-service-verification",
        summary="A case study that exercises one canonical API through browser rendering.",
        description="The fixture proves production service composition and discovery metadata.",
        architecture="PostgreSQL feeds FastAPI, Next.js, and the production Caddy edge.",
        is_open_source=False,
        nature=ProjectNature.SOFTWARE,
    )
    article = Article(
        title="Testing the Canonical Path",
        slug="testing-the-canonical-path",
        excerpt="Production-facing browser checks catch integration drift.",
        body_markdown="# Testing\n\nUse canonical contracts from persistence through rendering.",
        topics=["testing", "architecture"],
        reading_minutes=3,
    )
    hidden_project = Project(
        title="Private Draft Sentinel",
        slug="private-draft-sentinel",
        summary="This draft must never be retrieved by public search.",
        is_open_source=False,
        nature=ProjectNature.SOFTWARE,
    )
    PublicationPolicy.apply(project, PublicationStatus.PUBLISHED)
    PublicationPolicy.apply(article, PublicationStatus.PUBLISHED)
    PublicationPolicy.apply(hidden_project, PublicationStatus.DRAFT)

    async with database_client.session_factory() as session:
        session.add_all((project, article, hidden_project))
        await session.commit()

    async with database_client.session_factory() as session:
        projects = await PortfolioRepository(session).search_public_project_details(
            "What does the verification project prove?", limit=10
        )
        articles = await ContentRepository(session).search_public_articles(
            "What have you written about testing the canonical path?", limit=10
        )
        private_results = await PortfolioRepository(session).search_public_project_details(
            "Show me the private draft sentinel", limit=10
        )

    assert [item.slug for item in projects] == ["canonical-service-verification"]
    assert [item.slug for item in articles] == ["testing-the-canonical-path"]
    assert private_results == []


async def test_public_repositories_skip_stop_word_only_queries(
    database_client: DatabaseClient,
) -> None:
    async with database_client.session_factory() as session:
        assert (
            await PortfolioRepository(session).search_public_project_details(
                "What does it do?", limit=10
            )
            == []
        )
        assert (
            await ContentRepository(session).search_public_articles("What does it do?", limit=10)
            == []
        )
