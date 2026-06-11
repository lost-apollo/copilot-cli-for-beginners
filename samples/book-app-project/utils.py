from typing import Iterable

from books import Book, ValidationError


def format_menu() -> str:
    return "\n📚 Book Collection App\n1. Add a book\n2. List books\n3. Mark book as read\n4. Remove a book\n5. Exit"


def print_menu() -> None:
    print(format_menu())


def get_user_choice() -> str:
    return input("Choose an option (1-5): ").strip()


def validate_required_input(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValidationError(f"{field_name} is required.")


def get_required_input(prompt: str, field_name: str) -> str:
    value = input(prompt).strip()
    validate_required_input(value, field_name)
    return value


def parse_year(year_input: str) -> int:
    try:
        year = int(year_input)
    except ValueError:
        raise ValidationError("Year must be a number.") from None

    if year <= 0:
        raise ValidationError("Year must be a positive integer.")

    return year


def get_book_details() -> tuple[str, str, int]:
    title = get_required_input("Title: ", "Title")
    author = get_required_input("Author: ", "Author")
    year_input = get_required_input("Year: ", "Year")
    year = parse_year(year_input)

    return title, author, year


def format_books(books: Iterable[Book]) -> str:
    book_list = list(books)
    if not book_list:
        return "No books found."

    lines = ["", "Your Book Collection:", ""]
    for index, book in enumerate(book_list, start=1):
        status = "✓" if book.read else " "
        lines.append(f"{index}. [{status}] {book.title} by {book.author} ({book.year})")

    lines.append("")
    return "\n".join(lines)


def print_books(books: Iterable[Book]) -> None:
    print(format_books(books))
