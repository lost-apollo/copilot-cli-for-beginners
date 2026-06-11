import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from books import Book, ValidationError
from utils import format_books, get_book_details, parse_year, validate_required_input


def test_validate_required_input_rejects_blank_value():
    with pytest.raises(ValidationError, match="Title is required."):
        validate_required_input("   ", "Title")


def test_parse_year_rejects_non_numeric_value():
    with pytest.raises(ValidationError, match="Year must be a number."):
        parse_year("nineteen eighty four")


def test_format_books_returns_expected_output():
    books = [Book(title="Dune", author="Frank Herbert", year=1965, read=True)]

    output = format_books(books)

    assert "Your Book Collection:" in output
    assert "1. [✓] Dune by Frank Herbert (1965)" in output


class TestGetBookDetails:
    """Tests for get_book_details."""

    def test_returns_details_for_valid_input(self, monkeypatch):
        inputs = iter(["Dune", "Frank Herbert", "1965"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        result = get_book_details()

        assert result == ("Dune", "Frank Herbert", 1965)

    @pytest.mark.parametrize(
        ("inputs", "message"),
        [
            (["", "Frank Herbert", "1965"], "Title is required."),
            (["Dune", "", "1965"], "Author is required."),
            (["Dune", "Frank Herbert", ""], "Year is required."),
        ],
    )
    def test_rejects_empty_required_values(self, monkeypatch, inputs, message):
        values = iter(inputs)
        monkeypatch.setattr("builtins.input", lambda prompt: next(values))

        with pytest.raises(ValidationError, match=rf"{message[:-1]}\."):
            get_book_details()

    @pytest.mark.parametrize(
        "year_input",
        ["nineteen eighty four", "19.84", "2024-01-01", "1965a"],
    )
    def test_rejects_invalid_year_formats(self, monkeypatch, year_input):
        inputs = iter(["Dune", "Frank Herbert", year_input])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        with pytest.raises(ValidationError, match="Year must be a number."):
            get_book_details()

    def test_accepts_very_long_title(self, monkeypatch):
        long_title = "A" * 500
        inputs = iter([long_title, "Frank Herbert", "1965"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        result = get_book_details()

        assert result == (long_title, "Frank Herbert", 1965)

    def test_accepts_special_characters_in_author_name(self, monkeypatch):
        inputs = iter(["Dune", "Gabriel Garcia Marquez-Sanchez, Jr.", "1967"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        result = get_book_details()

        assert result == ("Dune", "Gabriel Garcia Marquez-Sanchez, Jr.", 1967)
