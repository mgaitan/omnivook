# Omnivook, omnivore articles as a (daily) book 📚

Automates the process of generating an eBook from [Omnivore](https://omnivore.app/) articles and sending it via email to your Kindle device.


## Usage

The easiest way of running the latest version is using [uv](https://docs.astral.sh/uv/getting-started/installation/). 

For a one-time run:


```bash
OMNIVORE_APIKEY=<key> uvx omnivook
```

To install it permanently, use


```bash
uv tool install omnivook
```


To upgrade it:

```bash
uv tool upgrade omnivook
```


Then simply run 

```bash
OMNIVORE_APIKEY=<key> omnivook
```


By default it will generate an epub with the articles since the day before.  

Pass `--help` to see all the options.


Alternatively, you can install `omnivook` with pipx, pip, etc. 

## Automated daily ebook via email ⏰: Setup Github Action

Clone this repo and configure the following [GitHub Secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions) in your repository:

- **`OMNIVORE_APIKEY`**: Get yours at https://omnivore.app/settings/api 
- **`MAIL_CONNECTION`**: The SMTP connection URL in the format: `smtp://user:password@server:port`. If this is set, you don't need to provide `SERVER`, `USERNAME`, `PASSWORD`, `SERVER_PORT`, or `SECURE`.
- **`MAIL_FROM`**: The email address from which the eBook will be sent.
- **`MAIL_TO`**: The Kindle email address where the eBook will be delivered.

Alternatively, if `MAIL_CONNECTION` is not set, you can configure the following secrets individually:

- **`SERVER`**: The SMTP server address.
- **`USERNAME`**: The SMTP username.
- **`PASSWORD`**: The SMTP password.
- **`SERVER_PORT`**: The SMTP server port (optional, defaults to `465`).
- **`SECURE`**: Whether the SMTP connection is secure (optional, defaults to `true`).

This setup relies on the [action-send-mail](https://github.com/dawidd6/action-send-mail) GitHub Action for sending emails.

You can overwrite these environment variables if you want to change the dynamic setup of:
- **`PROJECT_NAME`** = a.k.a the file name of the epub. Default to omnivook_since_`<DATE>`_to_`<DATE>`.epub
- **`EPUB_TITLE`**: a.k.a the title of the document. Default to omnivook since `<DATE>` to `<DATE>`
- **`EPUB_AUTHORS`**: a.k.a  List of site names of all the articles. Default set to the repo owner

### Manual Trigger 🔧

You can manually trigger the workflow from the GitHub Actions tab. When triggering manually, you have the following options:

- **SINCE**: Specify the start date to filter articles (format `YYYY-MM-DD`). If not provided, defaults to the previous day.
- **archive**: A boolean flag (`true` or `false`) that determines whether to archive the articles after processing. Defaults to `true`.
- **label**: (optional) Specify a label to filter articles.
