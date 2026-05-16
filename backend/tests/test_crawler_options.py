from types import SimpleNamespace

from ingest.crawler import (
    DEFAULT_EXCLUDE_PATTERNS,
    DEFAULT_INCLUDE_PATTERNS,
    PageOutput,
    build_saved_content,
    default_include_patterns,
    extract_result_title,
    matches_any_pattern,
    normalize_patterns,
    resolve_include_url_patterns,
    resolve_scope_prefix,
    should_crawl_url,
)


def test_normalize_patterns_uses_defaults_only_when_value_is_omitted() -> None:
    assert normalize_patterns(None, DEFAULT_INCLUDE_PATTERNS) == DEFAULT_INCLUDE_PATTERNS
    assert normalize_patterns([], DEFAULT_INCLUDE_PATTERNS) == ()


def test_normalize_patterns_accepts_comma_newline_and_repeated_values() -> None:
    assert normalize_patterns(["/docs/", "/api/, /guide/\n/reference/"]) == (
        "/docs/",
        "/api/",
        "/guide/",
        "/reference/",
    )


def test_include_patterns_default_to_docs_prefix() -> None:
    assert resolve_include_url_patterns("https://example.com/", DEFAULT_INCLUDE_PATTERNS) == [
        "/docs/*"
    ]


def test_domain_scope_has_no_default_include_pattern() -> None:
    assert default_include_patterns("domain") == ()
    assert resolve_scope_prefix("https://docs.example.com/", (), "domain") == "https://docs.example.com"


def test_path_patterns_match_url_paths_for_seeded_urls() -> None:
    assert should_crawl_url(
        "https://docs.example.com/guide/intro",
        allowed_host="docs.example.com",
        include_patterns=["/guide/*"],
        exclude_patterns=[],
    )
    assert not should_crawl_url(
        "https://docs.example.com/blog/intro",
        allowed_host="docs.example.com",
        include_patterns=["/guide/*"],
        exclude_patterns=[],
    )


def test_default_exclude_patterns_skip_common_non_docs_urls() -> None:
    assert matches_any_pattern("https://example.com/docs/changelog", DEFAULT_EXCLUDE_PATTERNS)
    assert matches_any_pattern("https://example.com/docs/build/index.html", DEFAULT_EXCLUDE_PATTERNS)
    assert matches_any_pattern("https://example.com/docs/package-lock.json", DEFAULT_EXCLUDE_PATTERNS)


def test_saved_crawl_content_includes_normalized_page_title() -> None:
    result = SimpleNamespace(
        url="https://example.com/docs/api-reference",
        status_code=200,
        metadata={"title": "api reference for the HTTP SDK", "depth": 1},
        cleaned_html="",
        html="",
    )
    page_output = PageOutput("", ".md", "# Ignored Fallback", "raw_markdown")

    saved = build_saved_content(result, page_output)

    assert extract_result_title(result) == "API Reference for the HTTP SDK"
    assert "title: API Reference for the HTTP SDK" in saved
