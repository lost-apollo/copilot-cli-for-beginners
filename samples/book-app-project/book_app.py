import sys
from books import BookAppError, BookCollection
from utils import get_book_details, get_required_input, print_books


collection: BookCollection | None = None


def get_collection() -> BookCollection:
    global collection

    if collection is None:
        collection = BookCollection()

    return collection


def handle_list():
    books = get_collection().list_books()
    print_books(books)


def handle_add():
    print("\nAdd a New Book\n")

    title, author, year = get_book_details()
    get_collection().add_book(title, author, year)
    print("\nBook added successfully.\n")


def handle_remove():
    print("\nRemove a Book\n")

    title = get_required_input("Enter the title of the book to remove: ", "Title")
    get_collection().remove_book(title)
    print("\nBook removed successfully.\n")


def handle_find():
    print("\nFind Books by Author\n")

    author = get_required_input("Author name: ", "Author name")
    books = get_collection().find_by_author(author)

    print_books(books)


def show_help():
    print("""
Book Collection Helper

Commands:
  list     - Show all books
  add      - Add a new book
  remove   - Remove a book by title
  find     - Find books by author
  help     - Show this help message
""")


COMMAND_HANDLERS = {
    "list": handle_list,
    "add": handle_add,
    "remove": handle_remove,
    "find": handle_find,
    "help": show_help,
}


def main():
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    handler = COMMAND_HANDLERS.get(command)
    if handler is None:
        print("Unknown command.\n")
        show_help()
        return

    try:
        handler()
    except BookAppError as error:
        print(f"\nError: {error}\n")


if __name__ == "__main__":
    main()
