from src.utils.url import normalize_url


def test_blank_input_returns_empty_string():
    assert normalize_url("") == ""
    assert normalize_url("   ") == ""


def test_adds_https_scheme_when_missing():
    assert normalize_url("toonily.com/webtoon/x") == "https://toonily.com/webtoon/x"


def test_preserves_existing_scheme():
    assert normalize_url("http://toonily.com/webtoon/x") == "http://toonily.com/webtoon/x"
    assert normalize_url("https://toonily.com/webtoon/x") == "https://toonily.com/webtoon/x"


def test_strips_trailing_slash():
    assert normalize_url("https://toonily.com/webtoon/x/") == "https://toonily.com/webtoon/x"


def test_strips_surrounding_whitespace():
    assert normalize_url("   https://example.com/path  ") == "https://example.com/path"
