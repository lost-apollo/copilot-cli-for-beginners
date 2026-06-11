import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import book_app
from books import BookNotFoundError, ValidationError


def test_main_dispatches_known_command(monkeypatch):
    called = False

    def fake_handler():
        nonlocal called
        called = True

    monkeypatch.setitem(book_app.COMMAND_HANDLERS, "list", fake_handler)
    monkeypatch.setattr(sys, "argv", ["book_app.py", "list"])

    book_app.main()

    assert called is True


def test_main_shows_help_for_unknown_command(monkeypatch, capsys):
    help_called = False

    def fake_help():
        nonlocal help_called
        help_called = True

    monkeypatch.setattr(book_app, "show_help", fake_help)
    monkeypatch.setattr(sys, "argv", ["book_app.py", "unknown"])

    book_app.main()

    captured = capsys.readouterr()
    assert "Unknown command." in captured.out
    assert help_called is True


def test_handle_list_uses_shared_book_printer(monkeypatch):
    books = [SimpleNamespace(title="Dune", author="Frank Herbert", year=1965, read=True)]
    printed_books = None

    class FakeCollection:
        def list_books(self):
            return books

    def fake_print_books(received_books):
        nonlocal printed_books
        printed_books = received_books

    monkeypatch.setattr(book_app, "collection", FakeCollection())
    monkeypatch.setattr(book_app, "print_books", fake_print_books)

    book_app.handle_list()

    assert printed_books == books


def test_handle_add_rejects_invalid_details(monkeypatch, capsys):
    def fake_get_book_details():
        raise ValidationError("Title is required.")

    monkeypatch.setattr(book_app, "get_book_details", fake_get_book_details)
    monkeypatch.setattr(sys, "argv", ["book_app.py", "add"])

    book_app.main()

    captured = capsys.readouterr()
    assert "Error: Title is required." in captured.out


def test_handle_add_saves_valid_book(monkeypatch, capsys):
    added_book = None

    class FakeCollection:
        def add_book(self, title, author, year):
            nonlocal added_book
            added_book = (title, author, year)

    monkeypatch.setattr(book_app, "collection", FakeCollection())
    monkeypatch.setattr(book_app, "get_book_details", lambda: ("Dune", "Frank Herbert", 1965))

    book_app.handle_add()

    captured = capsys.readouterr()
    assert added_book == ("Dune", "Frank Herbert", 1965)
    assert "Book added successfully." in captured.out


def test_handle_remove_rejects_empty_title(monkeypatch, capsys):
    def fake_get_required_input(prompt, field_name):
        raise ValidationError("Title is required.")

    monkeypatch.setattr(book_app, "get_required_input", fake_get_required_input)
    monkeypatch.setattr(sys, "argv", ["book_app.py", "remove"])

    book_app.main()

    captured = capsys.readouterr()
    assert "Error: Title is required." in captured.out


def test_handle_remove_reports_missing_book(monkeypatch, capsys):
    class FakeCollection:
        def remove_book(self, title):
            raise BookNotFoundError(f'Book "{title}" was not found.')

    monkeypatch.setattr(book_app, "collection", FakeCollection())
    monkeypatch.setattr(book_app, "get_required_input", lambda prompt, field_name: "Missing")
    monkeypatch.setattr(sys, "argv", ["book_app.py", "remove"])

    book_app.main()

    captured = capsys.readouterr()
    assert 'Error: Book "Missing" was not found.' in captured.out


def test_handle_find_rejects_empty_author(monkeypatch, capsys):
    def fake_get_required_input(prompt, field_name):
        raise ValidationError("Author name is required.")

    monkeypatch.setattr(book_app, "get_required_input", fake_get_required_input)
    monkeypatch.setattr(sys, "argv", ["book_app.py", "find"])

    book_app.main()

    captured = capsys.readouterr()
    assert "Error: Author name is required." in captured.out
