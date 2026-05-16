from ingest.cleaning import (
    clean_document_text,
    extract_metadata_title,
    extract_source_url,
    infer_document_title,
    normalize_title,
    title_from_path,
)


def test_clean_document_text_removes_crawl_metadata_and_page_chrome() -> None:
    raw = """<!--
source_url: https://neon.com/docs/guides/vercel-connection-methods
status_code: 200
depth: 2
saved_at: 2026-05-14T00:00:00Z
-->
[Team accounts with unlimited members now available](https://neon.com/docs/changelog)
Search...⌘K
Ask AI
* Connect

# Connecting to Neon from Vercel
Copy page

We recommend using a standard Postgres TCP driver.

Was this page helpful?
YesNo
"""

    cleaned = clean_document_text(raw)

    assert "source_url:" not in cleaned
    assert "Search..." not in cleaned
    assert "Copy page" not in cleaned
    assert "# Connecting to Neon from Vercel" in cleaned
    assert "standard Postgres TCP driver" in cleaned


def test_extract_source_url_and_infer_content_title() -> None:
    raw = """<!--
source_url: https://neon.com/docs/serverless/serverless-driver
depth: 2
-->
Search...⌘K
# Neon serverless driver
"""

    assert extract_source_url(raw) == "https://neon.com/docs/serverless/serverless-driver"
    assert infer_document_title(raw, "docs/serverless/serverless-driver/index.md") == (
        "Neon Serverless Driver"
    )


def test_infer_document_title_prefers_normalized_metadata_title() -> None:
    raw = """<!--
source_url: https://example.com/docs/api-reference
title: api reference: using the CLI & SDK
depth: 2
-->
# Fallback Heading
"""

    assert extract_metadata_title(raw) == "API Reference: Using the CLI & SDK"
    assert infer_document_title(raw, "docs/api-reference/index.md") == "API Reference: Using the CLI & SDK"


def test_title_from_path_normalizes_local_doc_file_names() -> None:
    assert title_from_path("guides/auth/README.md") == "Auth"
    assert title_from_path("api-reference/oauth_setup.md") == "OAuth Setup"
    assert normalize_title("connecting to neon from vercel") == "Connecting to Neon from Vercel"
