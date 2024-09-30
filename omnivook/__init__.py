import argparse
import logging
import os
import re
import shutil
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
import importlib.resources as pkg_resources

from omnivoreql import OmnivoreQL
from rich import print
from rich.logging import RichHandler

__version__ = "0.1.6"

logging.basicConfig(
    level="DEBUG",
    handlers=[RichHandler(show_time=False, markup=True)],
    format="%(message)s",
)
logger = logging.getLogger(__file__)

__client = None
__username = None

YESTERDAY = date.today() - timedelta(days=1)


def get_client() -> OmnivoreQL:
    global __client
    if __client is None:
        __client = OmnivoreQL(
            os.environ.get("OMNIVORE_APIKEY", os.environ.get("OMNIVORE_TOKEN"))
        )
    return __client


def get_username() -> str:
    global __username
    if __username is None:
        __username = get_client().get_profile()["me"]["profile"]["username"]
    return __username


def setup_source_folder():
    """Set up a source folder with the necessary Sphinx configuration."""

    source_dir = Path("./source")
    with pkg_resources.path("omnivook", "source_template") as source_template:
        shutil.copytree(source_template, source_dir)
    return source_dir


def get_articles(
    since=YESTERDAY, labels=None, exclude_labels=None, add_labels=None, archive=False, extra_filters=None
):
    articles = []
    after = 0
    query = f"in:inbox saved:{since.strftime('%Y-%m-%d')}..* readPosition:<60 sort:saved-desc"

    if labels:
        label_query = " ".join(f"label:{label}" for label in labels)
        query += f" {label_query}"

    if exclude_labels:
        exclude_query = " ".join(f"-label:{label}" for label in exclude_labels)
        query += f" {exclude_query}"

    if extra_filters:
        query += f" {extra_filters}"

    client = get_client()
    while True:
        page = client.get_articles(
            after=after,
            query=query,
        )
        articles.extend(page["search"]["edges"])

        if page["search"]["pageInfo"]["hasNextPage"]:
            after = page["search"]["pageInfo"]["endCursor"]
        else:
            assert page["search"]["pageInfo"]["totalCount"] == len(articles)
            logger.info(f"{len(articles)} articles retrieved")
            break

    source_path = setup_source_folder()
    for i, art in enumerate(articles):
        details = client.get_article(
            get_username(), art["node"]["slug"], format="markdown", include_content=True
        )["article"]["article"]

        node = art["node"]
        file_path = source_path / f"{i}_{node['slug']}.md"
        logger.info(f"Processing {node['originalArticleUrl']} -> {file_path}")
        full = (
            f"# {details['title']}\n\n"
            f"{details['originalArticleUrl']}\n\n"
            f"{details['content']}\n"
        )
        file_path.write_text(full)

        if add_labels:
            parsed_labels = [
                {"name": label, "color": "#0000FF", "description": ""}
                for label in add_labels
            ]
            client.set_page_labels_by_fields(
                page_id=details["id"], labels=parsed_labels
            )

        if archive:
            logger.info("Archiving...")
            client.archive_article(details["id"])
    return articles


def extract_warnings(output):
    # Regex to capture the details of the warnings
    warning_pattern = re.compile(
        r"(?P<file>source/[^:]+):(?P<line>\d+): WARNING: (?P<reason>.+)"
    )
    warnings = []

    for match in warning_pattern.finditer(output):
        warning_data = {
            "file": match.group("file"),
            "line": int(match.group("line")),
            "reason": match.group("reason"),
        }
        warnings.append(warning_data)

    return warnings


def apply_fix(warning):
    file_path = Path(warning["file"].replace(".md.md", ".md"))
    line_number = warning["line"]
    reason = warning["reason"]

    # Reading the file with pathlib
    lines = file_path.read_text().splitlines()

    if "lexer" in reason or "Lexing literal_block":
        # Case 1: Remove everything after "```" on the specific line
        logger.info(f"[green]Fixing lexer at {warning['file']}:{warning['line']}")
        lines[line_number - 1] = re.sub(r"```.*", "```", lines[line_number - 1])

    elif "header" in reason:
        # Case 2: Adjust header levels based on the warning
        logger.info(f"[green]Fixing header at {warning['file']}:{warning['line']}")
        match = re.search(r"H(?P<from>\d) to H(?P<to>\d)", reason)
        if match:
            from_level = int(match.group("from"))
            to_level = int(match.group("to"))

            new_level = from_level + 1 if to_level > from_level else from_level - 1

            # Replace the entire header prefix with the new level
            lines[line_number - 1] = re.sub(
                r"^#+", "#" * new_level, lines[line_number - 1]
            )

    elif "cross-reference target" in reason:
        # Case 3: Remove empty cross-reference links
        logger.info(
            f"[green]Fixing cross-reference target at {warning['file']}:{warning['line']}"
        )
        lines[line_number - 1] = re.sub(r"\[\]\(#.*?\)", "", lines[line_number - 1])

    else:
        # Unhandled warnings
        line_content = lines[line_number - 1].strip()
        logger.warning(
            f"[yellow]Unhandled warning[/yellow]: {file_path} at line {line_number} due to {reason}\n"
            f"[yellow]Line Content[/yellow]: {line_content}"
        )
    # Writing the corrected file back with pathlib
    file_path.write_text("\n".join(lines))


def run_sphinx_build(source_dir, title=None, max_attempts=3):
    attempt = 0
    warnings = []

    while attempt < max_attempts:
        attempt += 1
        logger.info(f"Attempt {attempt} of {max_attempts}...")
        if title:
            os.environ["EPUB_TITLE"] = title
        # Execute sphinx-build and capture the output
        result = subprocess.run(
            [
                "sphinx-build",
                "--keep-going",
                "-Eab",
                "epub",
                source_dir,
                str(source_dir / "_build" / "epub"),
            ],
            text=True,
            stderr=subprocess.PIPE,  # Capture only stderr for warnings
        )

        # Extract warnings from the stderr output
        warnings = extract_warnings(result.stderr)

        if not warnings:
            break

        # Apply fixes for the warnings
        for warning in warnings:
            apply_fix(warning)

        if attempt == max_attempts:
            logger.warning("Max attempts reached. Some warnings may still be present.")


def make_book(
    since=YESTERDAY, output_format="epub", authors_pages: list | None = None
) -> None:
    source_path = Path("source")
    md_files = list(source_path.glob("*.md"))

    if len(md_files) <= 1:  # only index.md
        logger.error("No articles found to compile.")
        return

    date = datetime.today()
    title = f"omnivook {since:%Y-%m-%d} to {date:%Y-%m-%d}"
    output = f"{title.replace(' ', '_')}.{output_format}"
    os.environ.setdefault("PROJECT_NAME", title.replace(" ", "_"))
    os.environ.setdefault("EPUB_TITLE", title)
    os.environ.setdefault("EPUB_AUTHORS", ",".join(authors_pages or []))
    logger.info(f"[bold]Generating {output}")
    print(f"PROJECT_NAME={title.replace(' ', '_')}")
    run_sphinx_build(source_dir=source_path, title=title)

    try:
        shutil.move(source_path / "_build" / "epub" / output, output)
        logger.info(f"[bold]Generated {output}")
    except FileNotFoundError:
        logger.error("Failed to generate the ebook.")


def main():
    parser = argparse.ArgumentParser(
        description="Generate an ebook from Omnivore articles"
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program's version number and exit",
    )
    parser.add_argument(
        "--since",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=YESTERDAY,
        help="Start date to filter articles (format YYYY-MM-DD)",
    )

    parser.add_argument(
        "--label",
        type=lambda s: [label.strip() for label in s.split(",")],
        help="Comma-separated labels to filter articles (optional)",
    )

    parser.add_argument(
        "--exclude-label",
        type=lambda s: [label.strip() for label in s.split(",")],
        help="Comma-separated labels to exclude articles (optional)",
    )
    parser.add_argument(
        "--add-label",
        type=lambda s: [label.strip() for label in s.split(",")],
        help="Comma-separated labels to add to exported articles",
    )
    parser.add_argument(
        "--extra-filter",
        type=str,
        help="Extra filter/s to apply to the search (e.g., 'language:spanish in:library')",
    )
    parser.add_argument(
        "-o",
        "--output-format",
        default="epub",
        help="Output format: epub, html, doc",
    )
    parser.add_argument(
        "--archive", action="store_true", help="Archive exported articles"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["all", "retrieve", "build"],
        default="all",
        help="Operation mode: all (default), retrieve (only get articles), build (only create book)",
    )

    args = parser.parse_args()

    if args.mode in ["all", "retrieve"]:
        articles = get_articles(
            since=args.since,
            labels=args.label,
            exclude_labels=args.exclude_label,
            add_labels=args.add_label,
            archive=args.archive,
        )

    if args.mode in ["all", "build"]:
        # in "build" only mode we don't have raw articles list.
        try:
            articles_authors_pages = [
                site_name for art in articles if (site_name := art["node"]["siteName"])
            ]
        except NameError:
            articles_authors_pages = None
        make_book(
            since=args.since,
            output_format=args.output_format,
            authors_pages=articles_authors_pages,
        )

    if args.mode == "all":
        shutil.rmtree("./source")


if __name__ == "__main__":
    main()
