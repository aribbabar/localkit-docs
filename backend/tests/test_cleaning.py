from ingest.cleaning import clean_document_text, extract_source_url, infer_document_title


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
        "Neon serverless driver"
    )
