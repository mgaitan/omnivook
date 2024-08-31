import os 

project = 'omnivook'
copyright = '2024, Martín Gaitán'
author = 'Martín Gaitán'

extensions = ["myst_parser"]
source_suffix = {'.md': 'markdown'}

epub_title = 'Omnivook'
epub_author = 'Martin Gaitan'
epub_show_urls = 'no'
version = f'0.1.{os.environ.get("GITHUB_RUN_ID", 0)}'
suppress_warnings = ["epub.unknown_project_files"]