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
YESTERDAY = date.today() - timedelta(days=2)


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
        "-o", 
        "--output-format",
        default="epub",
        help="Output format: epub, html, doc",
    )
    parser.add_argument(
        "--archive", action="store_true", help="Archive exported articles"
    )

    args = parser.parse_args()
    articles = get_articles(args.label, args.since, archive=args.archive)
    make_book(articles, since=args.since, output_format=args.output_format)
    return articles



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


def make_book(articles, since=YESTERDAY, output_format='epub'):

    if not articles:
        return
    for i, art in enumerate(articles):
        node = art["node"]
        print(f"processing {node['originalArticleUrl']}")
        full = (
            f"# {node['title']}\n\n"
            f"{node['originalArticleUrl']}\n\n"
            f"{node['content']}\n"
        )
        (Path("source") / f"{i}_{node['slug']}.md").write_text(full)

        date = datetime.today()
        title = f"omnivook {since:%Y-%m-%d} to {date:%Y-%m-%d}"
        output = f"{title.replace(' ','_')}.{output_format}"
        print(f"Generating {output}")
        subprocess.run(['sphinx-build', '-b', 'epub', 'source', '_build/epub'])

        # subprocess.run(
        #     [
        #         "pandoc",
        #         *glob(f"{d}/*.md"),
        #         "--epub-metadata=metadata.xml",
        #         f'--metadata=title:"{title}"',
        #         '--metadata=author:"Omnivore"',
        #         "--toc",
        #         "--toc-depth=1",
        #         "-o",
        #         output,
        #     ]
        # )
        

if __name__ == "__main__":
    main()
