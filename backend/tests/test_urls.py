from core.urls import canonical_url_from_origin_path


def test_canonical_url_from_remote_origin_and_markdown_path() -> None:
    assert canonical_url_from_origin_path(
        "https://neon.com/docs/introduction",
        "docs/guides/vercel-connection-methods/index.md",
    ) == "https://neon.com/docs/guides/vercel-connection-methods"


def test_canonical_url_ignores_local_origins() -> None:
    assert canonical_url_from_origin_path(
        "browser-upload:docs",
        "docs/index.md",
    ) is None
