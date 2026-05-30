"""Tests for tools/doc_intelligence.py — runs in STUB_MODE=true."""
import os
import pytest

os.environ["STUB_MODE"] = "true"

from tools.doc_intelligence import parse_rfp


def test_parse_rfp_stub_returns_correct_shape():
    result = parse_rfp("tests/sample_rfp.pdf")
    assert isinstance(result, dict), "Result must be a dict"
    assert "full_text" in result
    assert "pages" in result
    assert "sections" in result


def test_parse_rfp_stub_full_text_nonempty():
    result = parse_rfp("tests/sample_rfp.pdf")
    assert isinstance(result["full_text"], str)
    assert len(result["full_text"]) > 50


def test_parse_rfp_stub_pages_positive():
    result = parse_rfp("tests/sample_rfp.pdf")
    assert isinstance(result["pages"], int)
    assert result["pages"] > 0


def test_parse_rfp_stub_sections_structure():
    result = parse_rfp("tests/sample_rfp.pdf")
    assert isinstance(result["sections"], list)
    assert len(result["sections"]) >= 1
    for section in result["sections"]:
        assert "heading" in section
        assert "content" in section
        assert isinstance(section["heading"], str)
        assert isinstance(section["content"], str)


def test_parse_rfp_file_not_found_raises():
    os.environ["STUB_MODE"] = "false"
    try:
        with pytest.raises(FileNotFoundError):
            parse_rfp("nonexistent_file.pdf")
    finally:
        os.environ["STUB_MODE"] = "true"
