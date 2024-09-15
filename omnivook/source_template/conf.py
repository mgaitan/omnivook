import os

project = os.environ.get("PROJECT_NAME", "omnivook")
copyright = "2024, Martín Gaitán"
author = "Martín Gaitán"

extensions = ["myst_parser"]
source_suffix = {".md": "markdown"}

epub_title = os.environ.get("EPUB_TITLE", "Omnivook")
epub_author = os.environ.get(
    "EPUB_AUTHORS", os.environ.get("GITHUB_REPOSITORY_OWNER", "Martín Gaitán")
)
epub_show_urls = "no"
version = f'0.1.{os.environ.get("GITHUB_RUN_ID", 0)}'
suppress_warnings = ["epub.unknown_project_files"]
