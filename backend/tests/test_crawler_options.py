from ingest.crawler import (
    DEFAULT_EXCLUDE_PATTERNS,
    DEFAULT_INCLUDE_PATTERNS,
    matches_any_pattern,
    normalize_patterns,
    resolve_include_url_patterns,
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


def test_default_exclude_patterns_skip_common_non_docs_urls() -> None:
    assert matches_any_pattern("https://example.com/docs/changelog", DEFAULT_EXCLUDE_PATTERNS)
    assert matches_any_pattern("https://example.com/docs/build/index.html", DEFAULT_EXCLUDE_PATTERNS)
    assert matches_any_pattern("https://example.com/docs/package-lock.json", DEFAULT_EXCLUDE_PATTERNS)
