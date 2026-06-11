import os
import sys
import builtins
from contextlib import contextmanager
from io import StringIO

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import books
from books import BookCollection, BookNotFoundError, StorageError, ValidationError


@pytest.fixture(autouse=True)
def use_temp_data_file(tmp_path, monkeypatch):
    """Use a temporary data file for each test."""
    temp_file = tmp_path / "data.json"
    temp_file.write_text("[]")
    monkeypatch.setattr(books, "DATA_FILE", str(temp_file))
    return temp_file


@pytest.fixture
def collection():
    """Provide a fresh collection backed by a temporary data file."""
    return BookCollection()


class TestValidateRequiredText:
    """Tests for validate_required_text."""

    @pytest.mark.parametrize(
        ("value", "field_name"),
        [
            ("", "Title"),
            ("   ", "Author"),
        ],
    )
    def test_rejects_blank_values(self, value, field_name):
        with pytest.raises(ValidationError, match=rf"{field_name} is required\."):
            books.validate_required_text(value, field_name)

    def test_accepts_non_blank_value(self):
        books.validate_required_text("Dune", "Title")


class TestValidateBookData:
    """Tests for validate_book_data."""

    @pytest.mark.parametrize(
        ("title", "author", "year", "message"),
        [
            ("", "Frank Herbert", 1965, "Title is required."),
            ("Dune", "", 1965, "Author is required."),
            ("Dune", "Frank Herbert", 0, "Year must be a positive integer."),
        ],
    )
    def test_rejects_invalid_values(self, title, author, year, message):
        with pytest.raises(ValidationError, match=rf"{message[:-1]}\."):
            books.validate_book_data(title, author, year)

    def test_accepts_valid_values(self):
        books.validate_book_data("Dune", "Frank Herbert", 1965)


class TestBookCollectionInitialization:
    """Tests for BookCollection initialization and loading."""

    def test_starts_empty_when_file_is_missing(self, monkeypatch, tmp_path):
        missing_file = tmp_path / "missing.json"
        monkeypatch.setattr(books, "DATA_FILE", str(missing_file))

        result = BookCollection()

        assert result.books == []

    def test_loads_existing_books_from_json(self, tmp_path, monkeypatch):
        data_file = tmp_path / "data.json"
        data_file.write_text(
            '[{"title": "Dune", "author": "Frank Herbert", "year": 1965, "read": true}]'
        )
        monkeypatch.setattr(books, "DATA_FILE", str(data_file))

        result = BookCollection()

        assert len(result.books) == 1
        assert result.books[0].title == "Dune"
        assert result.books[0].read is True

    def test_raises_storage_error_for_corrupted_json(self, tmp_path, monkeypatch):
        temp_file = tmp_path / "data.json"
        temp_file.write_text("{not valid json}")
        monkeypatch.setattr(books, "DATA_FILE", str(temp_file))

        with pytest.raises(StorageError, match="Could not load books from"):
            BookCollection()

    def test_load_books_uses_file_context_manager(self, monkeypatch):
        calls = []

        @contextmanager
        def fake_open_data_file(self, mode, action):
            calls.append((mode, action))
            yield StringIO("[]")

        monkeypatch.setattr(BookCollection, "_open_data_file", fake_open_data_file)

        BookCollection()

        assert calls == [("r", "load books from")]


class TestAddBook:
    """Tests for add_book."""

    def test_adds_book_and_persists_it(self, collection, use_temp_data_file):
        book = collection.add_book("1984", "George Orwell", 1949)

        assert book.title == "1984"
        assert book.author == "George Orwell"
        assert book.year == 1949
        assert book.read is False
        assert len(collection.books) == 1
        assert '"title": "1984"' in use_temp_data_file.read_text()

    def test_allows_duplicate_books_with_same_title_and_author(self, collection):
        collection.add_book("Dune", "Frank Herbert", 1965)
        collection.add_book("Dune", "Frank Herbert", 1965)

        result = collection.list_books()

        assert len(result) == 2
        assert [book.title for book in result] == ["Dune", "Dune"]

    @pytest.mark.parametrize(
        ("title", "author", "year", "message"),
        [
            ("", "Frank Herbert", 1965, "Title is required."),
            ("Dune", "", 1965, "Author is required."),
            ("Dune", "Frank Herbert", -1, "Year must be a positive integer."),
        ],
    )
    def test_rejects_invalid_input(self, collection, title, author, year, message):
        with pytest.raises(ValidationError, match=rf"{message[:-1]}\."):
            collection.add_book(title, author, year)

    def test_rolls_back_in_memory_book_when_save_fails(self, collection, monkeypatch):
        def fail_save():
            raise StorageError("save failed")

        monkeypatch.setattr(collection, "save_books", fail_save)

        with pytest.raises(StorageError, match="save failed"):
            collection.add_book("Dune", "Frank Herbert", 1965)

        assert collection.books == []


class TestSaveBooks:
    """Tests for save_books."""

    def test_uses_file_context_manager(self, collection, monkeypatch):
        calls = []

        @contextmanager
        def fake_open_data_file(self, mode, action):
            calls.append((mode, action))
            yield StringIO()

        monkeypatch.setattr(BookCollection, "_open_data_file", fake_open_data_file)

        collection.save_books()

        assert calls == [("w", "save books to")]

    def test_raises_storage_error_for_file_permission_errors(self, collection, monkeypatch):
        original_open = builtins.open

        def fake_open(path, mode="r", *args, **kwargs):
            if "w" in mode:
                raise PermissionError("permission denied")
            return original_open(path, mode, *args, **kwargs)

        monkeypatch.setattr("builtins.open", fake_open)

        with pytest.raises(StorageError, match="Could not save books to"):
            collection.save_books()


class TestListBooks:
    """Tests for list_books."""

    def test_returns_internal_books_list(self, collection):
        collection.add_book("Dune", "Frank Herbert", 1965)

        result = collection.list_books()

        assert result is collection.books
        assert len(result) == 1


class TestFindBookByTitle:
    """Tests for find_book_by_title."""

    def test_returns_none_when_collection_is_empty(self, collection):
        assert collection.find_book_by_title("Dune") is None

    def test_finds_book_case_insensitively(self, collection):
        collection.add_book("Dune", "Frank Herbert", 1965)

        result = collection.find_book_by_title("dUnE")

        assert result is not None
        assert result.author == "Frank Herbert"

    def test_treats_titles_with_distinct_surrounding_whitespace_as_different_books(self, collection):
        collection.add_book("Dune", "Frank Herbert", 1965)
        collection.add_book(" Dune ", "Whitespace Author", 1966)

        result = collection.find_book_by_title(" Dune ")

        assert result is not None
        assert result.author == "Whitespace Author"

    def test_returns_none_when_book_does_not_exist(self, collection):
        assert collection.find_book_by_title("Missing") is None

    def test_rejects_blank_title(self, collection):
        with pytest.raises(ValidationError, match="Title is required."):
            collection.find_book_by_title("   ")


class TestMarkAsRead:
    """Tests for mark_as_read."""

    def test_marks_existing_book_as_read(self, collection):
        collection.add_book("Dune", "Frank Herbert", 1965)

        collection.mark_as_read("Dune")

        book = collection.find_book_by_title("Dune")
        assert book is not None
        assert book.read is True

    def test_raises_when_book_does_not_exist(self, collection):
        with pytest.raises(BookNotFoundError, match='Book "Nonexistent Book" was not found.'):
            collection.mark_as_read("Nonexistent Book")

    def test_rolls_back_read_flag_when_save_fails(self, collection, monkeypatch):
        collection.add_book("Dune", "Frank Herbert", 1965)

        def fail_save():
            raise StorageError("save failed")

        monkeypatch.setattr(collection, "save_books", fail_save)

        with pytest.raises(StorageError, match="save failed"):
            collection.mark_as_read("Dune")

        book = collection.find_book_by_title("Dune")
        assert book is not None
        assert book.read is False


class TestRemoveBook:
    """Tests for remove_book."""

    def test_removes_existing_book(self, collection):
        collection.add_book("The Hobbit", "J.R.R. Tolkien", 1937)

        collection.remove_book("The Hobbit")

        assert collection.find_book_by_title("The Hobbit") is None

    def test_returns_not_found_feedback_for_empty_collection(self, collection):
        with pytest.raises(BookNotFoundError, match='Book "Nonexistent Book" was not found.'):
            collection.remove_book("Nonexistent Book")

    def test_does_not_remove_book_by_partial_title_match(self, collection):
        collection.add_book("The Hobbit", "J.R.R. Tolkien", 1937)

        with pytest.raises(
            BookNotFoundError,
            match=r'Book "Hobbit" was not found\. Did you mean "The Hobbit"\?',
        ):
            collection.remove_book("Hobbit")

        assert collection.find_book_by_title("The Hobbit") is not None

    def test_removes_book_case_insensitively(self, collection):
        collection.add_book("Dune", "Frank Herbert", 1965)

        collection.remove_book("dUnE")

        assert collection.find_book_by_title("Dune") is None

    def test_removes_whitespace_variant_without_removing_exact_title(self, collection):
        collection.add_book("Dune", "Frank Herbert", 1965)
        collection.add_book(" Dune ", "Whitespace Author", 1966)

        collection.remove_book(" Dune ")

        remaining_titles = [book.title for book in collection.list_books()]
        assert remaining_titles == ["Dune"]

    def test_returns_helpful_feedback_when_book_is_not_found(self, collection):
        collection.add_book("Dune", "Frank Herbert", 1965)
        collection.add_book("Dune Messiah", "Frank Herbert", 1969)

        with pytest.raises(
            BookNotFoundError,
            match=r'Book "Dunee" was not found\. Did you mean "Dune"\?',
        ):
            collection.remove_book("Dunee")

    def test_preserves_original_input_in_not_found_feedback(self, collection):
        collection.add_book("Dune", "Frank Herbert", 1965)

        with pytest.raises(
            BookNotFoundError,
            match=r'Book " Dune " was not found\. Did you mean "Dune"\?',
        ):
            collection.remove_book(" Dune ")

    def test_restores_book_when_save_fails(self, collection, monkeypatch):
        collection.add_book("Dune", "Frank Herbert", 1965)

        def fail_save():
            raise StorageError("save failed")

        monkeypatch.setattr(collection, "save_books", fail_save)

        with pytest.raises(StorageError, match="save failed"):
            collection.remove_book("Dune")

        assert collection.find_book_by_title("Dune") is not None

    def test_restores_book_to_original_position_when_save_fails(self, collection, monkeypatch):
        collection.add_book("Dune", "Frank Herbert", 1965)
        collection.add_book("1984", "George Orwell", 1949)

        def fail_save():
            raise StorageError("save failed")

        monkeypatch.setattr(collection, "save_books", fail_save)

        with pytest.raises(StorageError, match="save failed"):
            collection.remove_book("Dune")

        assert [book.title for book in collection.list_books()] == ["Dune", "1984"]


class TestFindByAuthor:
    """Tests for find_by_author."""

    def test_returns_empty_list_when_collection_is_empty(self, collection):
        assert collection.find_by_author("Frank Herbert") == []

    def test_returns_matching_books_case_insensitively(self, collection):
        collection.add_book("Dune", "Frank Herbert", 1965)
        collection.add_book("Children of Dune", "Frank Herbert", 1976)
        collection.add_book("1984", "George Orwell", 1949)

        result = collection.find_by_author("frank herbert")

        assert [book.title for book in result] == ["Dune", "Children of Dune"]

    @pytest.mark.parametrize(
        ("author_name", "expected_title"),
        [
            ("Jean-Paul Sartre", "Nausea"),
            ("Mary Wollstonecraft Shelley", "Frankenstein"),
            ("Gabriel Garcia Marquez", "One Hundred Years of Solitude"),
        ],
    )
    def test_matches_author_names_with_complex_spacing_and_punctuation(
        self,
        collection,
        author_name,
        expected_title,
    ):
        collection.add_book("Nausea", "Jean-Paul Sartre", 1938)
        collection.add_book("Frankenstein", "Mary Wollstonecraft Shelley", 1818)
        collection.add_book("One Hundred Years of Solitude", "Gabriel Garcia Marquez", 1967)

        result = collection.find_by_author(author_name)

        assert [book.title for book in result] == [expected_title]

    def test_matches_author_name_with_accented_characters(self, collection):
        collection.add_book("Blindness", "José Saramago", 1995)
        collection.add_book("Baltasar and Blimunda", "José Saramago", 1982)
        collection.add_book("The Stranger", "Albert Camus", 1942)

        result = collection.find_by_author("josé saramago")

        assert [book.title for book in result] == ["Blindness", "Baltasar and Blimunda"]

    def test_returns_empty_list_when_author_has_no_matches(self, collection):
        assert collection.find_by_author("Unknown Author") == []

    def test_rejects_blank_author(self, collection):
        with pytest.raises(ValidationError, match="Author is required."):
            collection.find_by_author("   ")

    def test_rejects_empty_string_author(self, collection):
        with pytest.raises(ValidationError, match="Author is required."):
            collection.find_by_author("")


class TestConcurrentAccess:
    """Tests for coordinating multiple BookCollection instances."""

    def test_second_instance_sees_changes_after_reloading(self):
        first_collection = BookCollection()
        second_collection = BookCollection()

        first_collection.add_book("Dune", "Frank Herbert", 1965)
        second_collection.load_books()

        result = second_collection.find_book_by_title("Dune")

        assert result is not None
        assert result.author == "Frank Herbert"

    def test_instances_can_append_books_sequentially_with_reload(self):
        first_collection = BookCollection()
        second_collection = BookCollection()

        first_collection.add_book("Dune", "Frank Herbert", 1965)
        second_collection.load_books()
        second_collection.add_book("1984", "George Orwell", 1949)
        first_collection.load_books()

        assert [book.title for book in first_collection.list_books()] == ["Dune", "1984"]
