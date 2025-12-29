from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import csv
from itertools import groupby
from operator import attrgetter


@dataclass
class Book:
    """A book from the bookshelf."""

    title: str
    subtitle: str
    author: str
    start_date: datetime  # When the book was started
    end_date: Optional[datetime] = (
        None  # When the book was finished (None if currently reading)
    )
    partial: bool = False  # Whether the book was only partially read
    link: str = ""  # URL to book info
    publish_year: int = 0
    additional_text: Optional[str] = None
    notes: bool = False
    row_order: int = 0  # Original order in CSV file, for tiebreaking

    @property
    def full_title(self) -> str:
        """The full title including subtitle if present."""
        if self.subtitle:
            return f"{self.title}: {self.subtitle}"
        return self.title

    @property
    def reading_year(self) -> Optional[int]:
        """The year the book was read (using end_date)."""
        return self.end_date.year if self.end_date else None

    @property
    def age_when_read(self) -> Optional[int]:
        """How old the book was when it was read."""
        return self.end_date.year - self.publish_year if self.end_date else None

    @property
    def is_currently_reading(self) -> bool:
        """Whether the book is currently being read (no end_date)."""
        return self.end_date is None

    def to_markdown(self) -> str:
        """Convert book to markdown format."""
        title = self.full_title
        if self.partial:
            title = f"*{title}*"

        entry = f"- [{title}]({self.link}) ({self.author}, {self.publish_year})"
        if self.additional_text:
            entry += f" [{self.additional_text}]"
        return entry


def load_books(path: str | Path) -> list[Book]:
    """Load books from a CSV file.

    Args:
        path: Path to the CSV file containing book data

    Returns:
        List of Book objects

    Raises:
        FileNotFoundError: If the CSV file doesn't exist
        ValueError: If the CSV data is invalid
    """
    books = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            # Convert empty strings to None for optional fields
            additional_text = row["Additional Text"] or None

            # Convert boolean strings to actual booleans
            partial = row["Partial"].lower() == "true"
            notes = row["Notes"].lower() == "true"

            # Parse dates in YYYY-MM-DD format
            start_date = datetime.strptime(row["Start Date"], "%Y-%m-%d")

            # Handle end_date - if empty, it's currently being read
            end_date = None
            if row["End Date"].strip():
                end_date = datetime.strptime(row["End Date"], "%Y-%m-%d")

            publish_year = int(row["Publish Year"]) if row["Publish Year"] else 0

            book = Book(
                title=row["Title"],
                subtitle=row["Subtitle"],
                author=row["Author"],
                start_date=start_date,
                end_date=end_date,
                partial=partial,
                link=row["Link"],
                publish_year=publish_year,
                additional_text=additional_text,
                notes=notes,
                row_order=i,  # Store the original row number
            )
            books.append(book)

    return books


def generate_bookshelf_markdown(books: list[Book], output_path: str | Path) -> None:
    """Generate a markdown file listing all books.

    Args:
        books: List of Book objects
        output_path: Where to write the markdown file
    """
    # Separate currently reading books from completed books
    currently_reading = [book for book in books if book.is_currently_reading]
    completed_books = [book for book in books if not book.is_currently_reading]

    # Sort completed books by end_date (newest first), using row_order as tiebreaker
    sorted_completed_books = sorted(
        completed_books, key=lambda b: (b.end_date, b.row_order), reverse=True
    )

    # Sort currently reading books by start_date (newest first), using row_order as tiebreaker
    sorted_currently_reading = sorted(
        currently_reading, key=lambda b: (b.start_date, b.row_order), reverse=True
    )

    # Group books by year
    lines = [
        "- A log of all the books and other long form content I've read since ~2021 in reverse chronological order.",
        "- *Italics* indicate I only skimmed/partially read.",
        f"- Last updated: {datetime.now().strftime('%B %d')}{datetime.now().strftime('%d').endswith('1') and 'st' or datetime.now().strftime('%d').endswith('2') and 'nd' or datetime.now().strftime('%d').endswith('3') and 'rd' or 'th'} {datetime.now().strftime('%Y')}.",
        "- Suggestions always welcome.",
    ]

    # Add currently reading section at the top if there are any
    if sorted_currently_reading:
        lines.append("## Currently Reading")
        lines.append("")
        for book in sorted_currently_reading:
            lines.append(book.to_markdown())
        lines.append("")

    # Group completed books by year, maintaining the sort order
    current_year = None
    for book in sorted_completed_books:
        if book.end_date.year != current_year:
            if current_year is not None:  # Add blank line between years
                lines.append("")
            current_year = book.end_date.year
            lines.append(f"## {current_year}")
            lines.append("")
        lines.append(book.to_markdown())

    # Add final blank line
    lines.append("")

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    # Example usage
    books = load_books("src/bookshelf.csv")
    print(f"Loaded {len(books)} books")

    # Generate the markdown file
    generate_bookshelf_markdown(books, "src/bookshelf.md")
    print("Generated bookshelf.md")
