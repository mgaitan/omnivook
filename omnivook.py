import argparse
import os
from datetime import date, timedelta
import subprocess
from pathlib import Path
from glob import glob
import tempfile
from datetime import datetime

from omnivoreql import OmnivoreQL

client = OmnivoreQL(os.environ.get("OMNIVORE_TOKEN"))

LABEL = "k"
YESTERDAY = date.today() - timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate an ebook from Omnivore articles"
    )
    parser.add_argument(
        "--label", type=str, default=LABEL, help="Label to filter articles"
    )
    parser.add_argument(
        "--since",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=YESTERDAY,
        help="Start date to filter articles (format YYYY-MM-DD)",
    )
    parser.add_argument(
        "--convert-to-mobi",
        action="store_true",
        help="Convert the output to .mobi format",
    )
    parser.add_argument(
        "--archive", action="store_true", help="Archive exported articles"
    )

    args = parser.parse_args()
    articles = get_articles(args.label, args.since, archive=args.archive)
    make_book(articles, since=args.since, convert_to_mobi=args.convert_to_mobi)


def get_articles(label=LABEL, since=YESTERDAY, archive=False):
    articles = []
    after = 0
    while True:
        page = client.get_articles(
            format="markdown",
            after=after,
            include_content=True,
            query=f"in:inbox saved:{YESTERDAY.strftime("%Y-%m-%d")}..* readPosition:<60 label:{LABEL} sort:saved-asc",
        )
        articles.extend(page["search"]["edges"])

        if page["search"]["pageInfo"]["hasNextPage"]:
            after = page["search"]["pageInfo"]["endCursor"]
        else:
            assert page["search"]["pageInfo"]["totalCount"] == len(articles)
            print(f"{len(articles)} articles retrieved")
            break
    if archive:
        print("Archiving...")
        for art in articles:
            client.archive_article(art["node"]["id"])
    return articles


def make_book(articles, since=YESTERDAY, convert_to_mobi=False):
    if not articles:
        return
    with tempfile.TemporaryDirectory() as d:
        for i, art in enumerate(articles):
            node = art["node"]
            print(f"processing {node['originalArticleUrl']}")
            full = f"# {node['title']}\n\n-{node['originalArticleUrl']}\n\n{node['content']}"
            (Path(d) / f"{i}_{node['slug']}.md").write_text(full)

        date = datetime.today()
        title = f"omnivook {since:%Y-%m-%d} to {date:%Y-%m-%d}"
        output = f"{title.replace(' ','_')}.epub"
        print(f"Generating {output}")
        subprocess.run(
            [
                "pandoc",
                *glob(f"{d}/*.md"),
                "--metadata",
                f'title="{title}"',
                # "--toc",
                # "--toc-depth=1",
                "-o",
                output,
            ]
        )
        if convert_to_mobi:
            subprocess.run(["ebook-convert", output, Path(output).with_suffix(".mobi")])


if __name__ == "__main__":
    main()
