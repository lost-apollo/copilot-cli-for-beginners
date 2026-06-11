from contextlib import contextmanager
from difflib import get_close_matches
import json
from dataclasses import dataclass, asdict
from typing import Iterator, List, Optional, TextIO

DATA_FILE = "data.json"


class BookAppError(Exception):
    """Base exception for book app errors."""


class ValidationError(BookAppError):
    """Raised when book data is invalid."""


class BookNotFoundError(BookAppError):
    """Raised when a requested book cannot be found."""


class StorageError(BookAppError):
    """Raised when loading or saving the collection fails."""


@dataclass
class Book:
    title: str
    author: str
    year: int
    read: bool = False


def normalize_text(value: str) -> str:
    """Normalize text for user-friendly, case-insensitive comparisons."""
    return value.casefold()


def find_similar_titles(books: List["Book"], title: str) -> List[str]:
    """Find likely title matches to help users recover from a failed lookup."""
    normalized_title = normalize_text(title)
    if not normalized_title:
        return []

    normalized_to_title: dict[str, str] = {}
    normalized_titles: List[str] = []
    for book in books:
        normalized_book_title = normalize_text(book.title)
        if normalized_book_title not in normalized_to_title:
            normalized_to_title[normalized_book_title] = book.title
            normalized_titles.append(normalized_book_title)

    suggestions: List[str] = []
    for normalized_book_title in normalized_titles:
        if (
            normalized_title in normalized_book_title
            or normalized_book_title in normalized_title
        ):
            suggestions.append(normalized_to_title[normalized_book_title])

    close_matches = get_close_matches(
        normalized_title,
        normalized_titles,
        n=3,
        cutoff=0.6,
    )
    for normalized_book_title in close_matches:
        title_match = normalized_to_title[normalized_book_title]
        if title_match not in suggestions:
            suggestions.append(title_match)

    return suggestions


def validate_required_text(value: str, field_name: str) -> None:
    """Ensure a required text value is not blank.

    Args:
        value (str): The text value to validate.
        field_name (str): The user-facing field name for error messages.

    Returns:
        None: This function returns nothing when validation succeeds.

    Raises:
        ValidationError: If the value is empty or only whitespace.

    Example:
        >>> validate_required_text("Dune", "Title")
        >>> validate_required_text("   ", "Title")
        Traceback (most recent call last):
        ...
        ValidationError: Title is required.
    """
    if not value.strip():
        raise ValidationError(f"{field_name} is required.")


def validate_book_data(title: str, author: str, year: int) -> None:
    """Validate the core fields needed to create a book.

    Args:
        title (str): The book title.
        author (str): The book author's name.
        year (int): The publication year.

    Returns:
        None: This function returns nothing when validation succeeds.

    Raises:
        ValidationError: If any field is blank or the year is not positive.

    Example:
        >>> validate_book_data("Dune", "Frank Herbert", 1965)
        >>> validate_book_data("", "Frank Herbert", 1965)
        Traceback (most recent call last):
        ...
        ValidationError: Title is required.
    """
    validate_required_text(title, "Title")
    validate_required_text(author, "Author")

    if year <= 0:
        raise ValidationError("Year must be a positive integer.")


class BookCollection:
    def __init__(self):
        """Create a book collection and load saved books from disk.

        Returns:
            None: This constructor initializes the collection in memory.

        Raises:
            StorageError: If the saved data file cannot be loaded.

        Example:
            >>> collection = BookCollection()
            >>> isinstance(collection.books, list)
            True
        """
        self.books: List[Book] = []
        self.load_books()

    @contextmanager
    def _open_data_file(self, mode: str, action: str) -> Iterator[TextIO]:
        """Open the collection data file for a read or write operation.

        Args:
            mode (str): The file mode to use, such as ``"r"`` or ``"w"``.
            action (str): The human-readable action used in storage error messages.

        Returns:
            Iterator[TextIO]: A context manager that yields the opened file object.

        Raises:
            FileNotFoundError: If the file is opened for reading and does not exist.
            StorageError: If the file cannot be opened for the requested action.

        Example:
            >>> collection = BookCollection()
            >>> with collection._open_data_file("r", "load books from") as data_file:
            ...     isinstance(data_file.read(), str)
            True
        """
        try:
            with open(DATA_FILE, mode, encoding="utf-8") as data_file:
                yield data_file
        except FileNotFoundError:
            if "r" in mode:
                raise
            raise StorageError(f"Could not {action} {DATA_FILE}.") from None
        except OSError as error:
            raise StorageError(f"Could not {action} {DATA_FILE}.") from error

    def load_books(self) -> None:
        """Load books from the JSON data file into memory.

        If the data file does not exist yet, the collection starts empty.

        Returns:
            None: This method updates ``self.books`` in place.

        Raises:
            StorageError: If the file cannot be read or contains invalid data.

        Example:
            >>> collection = BookCollection()
            >>> collection.load_books()
        """
        try:
            with self._open_data_file("r", "load books from") as data_file:
                data = json.load(data_file)
                self.books = [Book(**b) for b in data]
        except FileNotFoundError:
            self.books = []
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise StorageError(f"Could not load books from {DATA_FILE}.") from error

    def save_books(self) -> None:
        """Save the current in-memory book collection to the JSON data file.

        Returns:
            None: This method writes the current collection to disk.

        Raises:
            StorageError: If the collection cannot be written to disk.

        Example:
            >>> collection = BookCollection()
            >>> collection.add_book("Dune", "Frank Herbert", 1965)
            Book(title='Dune', author='Frank Herbert', year=1965, read=False)
            >>> collection.save_books()
        """
        with self._open_data_file("w", "save books to") as data_file:
            json.dump([asdict(b) for b in self.books], data_file, indent=2)

    def add_book(self, title: str, author: str, year: int) -> Book:
        """Create a new book, add it to the collection, and persist it.

        Args:
            title (str): The book title.
            author (str): The book author's name.
            year (int): The publication year.

        Returns:
            Book: The newly created book.

        Raises:
            ValidationError: If any book field is invalid.
            StorageError: If the updated collection cannot be saved.

        Example:
            >>> collection = BookCollection()
            >>> book = collection.add_book("Dune", "Frank Herbert", 1965)
            >>> book.title
            'Dune'
        """
        validate_book_data(title, author, year)
        book = Book(title=title, author=author, year=year)
        self.books.append(book)
        try:
            self.save_books()
        except StorageError:
            self.books.pop()
            raise
        return book

    def list_books(self) -> List[Book]:
        """Return all books currently stored in the collection.

        Returns:
            List[Book]: The books currently held in memory.

        Raises:
            None.

        Example:
            >>> collection = BookCollection()
            >>> isinstance(collection.list_books(), list)
            True
        """
        return self.books

    def find_book_by_title(self, title: str) -> Optional[Book]:
        """Find a single book by title using a case-insensitive match.

        Args:
            title (str): The title to search for.

        Returns:
            Optional[Book]: The matching book if found, otherwise ``None``.

        Raises:
            ValidationError: If the title is blank.

        Example:
            >>> collection = BookCollection()
            >>> collection.add_book("Dune", "Frank Herbert", 1965)
            Book(title='Dune', author='Frank Herbert', year=1965, read=False)
            >>> collection.find_book_by_title("dune").author
            'Frank Herbert'
        """
        validate_required_text(title, "Title")
        normalized_title = normalize_text(title)
        for book in self.books:
            if normalize_text(book.title) == normalized_title:
                return book
        return None

    def mark_as_read(self, title: str) -> None:
        """Mark a book as read and save the updated collection.

        Args:
            title (str): The title of the book to update.

        Returns:
            None: This method updates the matching book in place.

        Raises:
            ValidationError: If the title is blank.
            BookNotFoundError: If no book matches the title.
            StorageError: If the updated collection cannot be saved.

        Example:
            >>> collection = BookCollection()
            >>> collection.add_book("Dune", "Frank Herbert", 1965)
            Book(title='Dune', author='Frank Herbert', year=1965, read=False)
            >>> collection.mark_as_read("Dune")
            >>> collection.find_book_by_title("Dune").read
            True
        """
        book = self.find_book_by_title(title)
        if book is None:
            raise BookNotFoundError(f'Book "{title}" was not found.')

        book.read = True
        try:
            self.save_books()
        except StorageError:
            book.read = False
            raise

    def remove_book(self, title: str) -> None:
        """Remove a book from the collection by title.

        Args:
            title (str): The title of the book to remove.

        Returns:
            None: This method removes the matching book from the collection.

        Raises:
            ValidationError: If the title is blank.
            BookNotFoundError: If no book matches the title.
            StorageError: If the updated collection cannot be saved.

        Example:
            >>> collection = BookCollection()
            >>> collection.add_book("Dune", "Frank Herbert", 1965)
            Book(title='Dune', author='Frank Herbert', year=1965, read=False)
            >>> collection.remove_book("Dune")
            >>> collection.find_book_by_title("Dune") is None
            True
        """
        requested_title = title
        book = self.find_book_by_title(title)
        if book is None:
            close_matches = find_similar_titles(self.books, title)
            if close_matches:
                suggestions = ", ".join(f'"{match}"' for match in close_matches)
                raise BookNotFoundError(
                    f'Book "{requested_title}" was not found. Did you mean {suggestions}?'
                )
            raise BookNotFoundError(f'Book "{requested_title}" was not found.')

        original_index = self.books.index(book)
        self.books.pop(original_index)
        try:
            self.save_books()
        except StorageError:
            self.books.insert(original_index, book)
            raise

    def find_by_author(self, author: str) -> List[Book]:
        """Find all books by an author using a case-insensitive match.

        Args:
            author (str): The author name to search for.

        Returns:
            List[Book]: A list of matching books. The list is empty if no books match.

        Raises:
            ValidationError: If the author name is blank.

        Example:
            >>> collection = BookCollection()
            >>> collection.add_book("Dune", "Frank Herbert", 1965)
            Book(title='Dune', author='Frank Herbert', year=1965, read=False)
            >>> len(collection.find_by_author("frank herbert"))
            1
        """
        validate_required_text(author, "Author")
        normalized_author = normalize_text(author)
        return [b for b in self.books if normalize_text(b.author) == normalized_author]
