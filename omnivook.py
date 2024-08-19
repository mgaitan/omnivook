import argparse
import os
from datetime import date, timedelta, datetime
import subprocess
from pathlib import Path

from omnivoreql import OmnivoreQL

client = OmnivoreQL(os.environ.get("OMNIVORE_TOKEN"))

YESTERDAY = date.today() - timedelta(days=1)

def main():
    parser = argparse.ArgumentParser(
        description="Generate an ebook from Omnivore articles"
    )
    parser.add_argument(
        "--label", type=str, nargs='*', help="Labels to filter articles (optional, can be multiple)"
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
        help="Operation mode: all (default), retrieve (only get articles), build (only create book)"
    )

    args = parser.parse_args()

    if args.mode in ["all", "retrieve"]:
        articles = get_articles(labels=args.label, since=args.since, archive=args.archive)
    else:
        articles = None

    if args.mode in ["all", "build"]:
        make_book(since=args.since, output_format=args.output_format)

    return articles

def get_articles(labels=None, since=YESTERDAY, archive=False):
    articles = []
    after = 0
    query = f"in:inbox saved:{since.strftime('%Y-%m-%d')}..* readPosition:<60 sort:saved-desc"
    if labels:
        label_query = ' '.join(f"label:{label}" for label in labels)
        query += f" {label_query}"
    
    while True:
        page = client.get_articles(
            # format="markdown",
            after=after,
            include_content=True,
            query=query,
        )
        articles.extend(page["search"]["edges"])

        if page["search"]["pageInfo"]["hasNextPage"]:
            after = page["search"]["pageInfo"]["endCursor"]
        else:
            assert page["search"]["pageInfo"]["totalCount"] == len(articles)
            print(f"{len(articles)} articles retrieved")
            break

    for i, art in enumerate(articles):
        node = art["node"]
        print(f"Processing {node['originalArticleUrl']}\n--------------")
        print(node)
        
        full = (
            f"# {node['title']}\n\n"
            f"{node['originalArticleUrl']}\n\n"
            f"{node['content']}\n"
        )
        (Path("source") / f"{i}_{node['slug']}.md").write_text(full)

        if archive:
            print("Archiving...")
            client.archive_article(node["id"])
    return articles

def make_book(since=YESTERDAY, output_format='epub'):
    source_path = Path("source")
    md_files = list(source_path.glob("*.md"))
    
    if len(md_files) <= 1:  # only index.md
        print("No articles found to compile.")
        return

    date = datetime.today()
    title = f"omnivook {since:%Y-%m-%d} to {date:%Y-%m-%d}"
    output = f"{title.replace(' ', '_')}.{output_format}"
    print(f"Generating {output}")
    subprocess.run(['sphinx-build', '-b', output_format, 'source', f'_build/{output_format}'])

if __name__ == "__main__":
    main()
