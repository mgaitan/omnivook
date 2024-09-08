import argparse
import logging
import os
import re
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

from omnivoreql import OmnivoreQL
from rich.logging import RichHandler


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
        __client = OmnivoreQL(os.environ.get("OMNIVORE_TOKEN"))
    return __client


def get_username() -> str:
    global __username
    if __username is None:
        __username = get_client().get_profile()["me"]["profile"]["username"]
    return __username


def main():
    parser = argparse.ArgumentParser(
        description="Generate an ebook from Omnivore articles"
    )
    parser.add_argument(
        "--label",
        type=str,
        nargs="*",
        help="Labels to filter articles (optional, can be multiple)",
    )
    parser.add_argument(
        "--since",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=YESTERDAY,
        help="Start date to filter articles (format YYYY-MM-DD)",
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
            labels=args.label, since=args.since, archive=args.archive
        )
    else:
        articles = None

    articles_authors_pages = [art.get('node').get('siteName') for art in articles if art['node']['siteName']]

    if args.mode in ["all", "build"]:
        make_book(since=args.since, output_format=args.output_format, authors_pages=articles_authors_pages)

    return articles


def get_articles(labels=None, since=YESTERDAY, archive=False):
    articles = []
    after = 0
    query = f"in:inbox saved:{since.strftime('%Y-%m-%d')}..* readPosition:<60 sort:saved-desc"
    if labels:
        label_query = " ".join(f"label:{label}" for label in labels)
        query += f" {label_query}"

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

    for i, art in enumerate(articles):
        details = client.get_article(
            get_username(), art["node"]["slug"], format="markdown", include_content=True
        )["article"]["article"]

        node = art["node"]
        file_path = (Path("source") / f"{i}_{node['slug']}.md")
        logger.info(f"Processing {node['originalArticleUrl']} -> {file_path}")
        full = (
            f"# {details['title']}\n\n"
            f"{details['originalArticleUrl']}\n\n"
            f"{details['content']}\n"
        )
        file_path.write_text(full)

        if archive:
            logger.info("Archiving...")
            client.archive_article(details["id"])
    return articles


def extract_warnings(output):
    # Regex to capture the details of the warnings
    warning_pattern = re.compile(
        r"(?P<file>source/[^:]+):(?P<line>\d+): WARNING: (?P<reason>.+)"
    )

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

    if "lexer" in reason:
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
            lines[line_number - 1] = re.sub(r"^#+", "#" * new_level, lines[line_number - 1])

    elif "cross-reference target" in reason:
        # Case 3: Remove empty cross-reference links
        logger.info(f"[green]Fixing cross-reference target at {warning['file']}:{warning['line']}")
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


def run_sphinx_build(title=None, max_attempts=3):
    attempt = 0
    warnings = []

    while attempt < max_attempts:
        attempt += 1
        logger.info(f"Attempt {attempt} of {max_attempts}...")
        if title:
            os.environ["EPUB_TITLE"] = title
        # Execute sphinx-build and capture the output
        result = subprocess.run(
            ["sphinx-build", "--keep-going", "-Eab", "epub", "source", "_build/epub"],
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


def make_book(since=YESTERDAY, output_format="epub", authors_pages: list = None) -> None:
    source_path = Path("source")
    md_files = list(source_path.glob("*.md"))

    if len(md_files) <= 1:  # only index.md
        logger.error("No articles found to compile.")
        return

    date = datetime.today()
    title = f"omnivook {since:%Y-%m-%d} to {date:%Y-%m-%d}"
    output = f"{title.replace(' ', '_')}.{output_format}"
    os.environ["PROJECT_NAME"] = os.environ.get("PROJECT_NAME", f"{title.replace(' ', '_')}")
    os.environ["EPUB_TITLE"] = os.environ.get("EPUB_TITLE", title)
    authors_sites = ",".join(authors_pages)
    os.environ["EPUB_AUTHORS"] = os.environ.get("EPUB_AUTHORS", authors_sites)
    logger.info(f"[bold]Generating {output}")
    run_sphinx_build()


if __name__ == "__main__":
    main()
