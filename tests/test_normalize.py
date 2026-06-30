from transformer.normalize import normalize_country, normalize_date, normalize_email, normalize_phone
from transformer.skills import canonicalize_skill


def test_phone_e164_with_default_region() -> None:
    assert normalize_phone("9876543210", "IN") == "+919876543210"
    assert normalize_phone("see resume", "IN") is None
    assert normalize_phone("+1 call me", "US") is None


def test_date_normalization() -> None:
    assert normalize_date("Jan 2023") == "2023-01"
    assert normalize_date("2023") == "2023-01"
    assert normalize_date("not a date") is None


def test_country_normalization() -> None:
    assert normalize_country("India") == "IN"
    assert normalize_country("USA") == "US"
    assert normalize_country("Atlantis") is None


def test_email_normalization() -> None:
    assert normalize_email(" PERSON@Example.COM ") == "person@example.com"
    assert normalize_email("N/A") is None
    assert normalize_email("bad-email") is None


def test_skill_canonicalization() -> None:
    assert canonicalize_skill("py") == ("Python", True)
    assert canonicalize_skill("gh actions") == ("GitHub Actions", True)
    assert canonicalize_skill("k8s") == ("Kubernetes", True)
    assert canonicalize_skill("data wrangling") == ("Data Wrangling", False)
    assert canonicalize_skill("see resume") == (None, False)
