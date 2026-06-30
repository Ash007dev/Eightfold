"""Acronym skills must not be mangled by fallback title-casing."""

from transformer.skills import canonicalize_skill


def test_acronym_and_language_canonicalization() -> None:
    assert canonicalize_skill("CSS") == ("CSS", True)
    assert canonicalize_skill("SQL") == ("SQL", True)
    assert canonicalize_skill("c++") == ("C++", True)
    assert canonicalize_skill("c#") == ("C#", True)
    assert canonicalize_skill("golang") == ("Go", True)
