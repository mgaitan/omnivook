# Omnivook, omnivore articles as a (daily) book 📚

Automates the process of generating an eBook from [Omnivore](https://omnivore.app/) articles and sending it via email to your Kindle device.


## Usage 🚀

### Automated Daily Run ⏰

Every article saved in the last day that hasn't been read (`readPosition:<60`) and isn't archived with the label `k` will be sent as a book automatically every day at 17:30 Argentina time (20:30 UTC). 

### Manual Trigger 🔧

You can manually trigger the workflow from the GitHub Actions tab. When triggering manually, you have the following options:

- **SINCE**: Specify the start date to filter articles (format `YYYY-MM-DD`). If not provided, defaults to the previous day.
- **archive**: A boolean flag (`true` or `false`) that determines whether to archive the articles after processing. Defaults to `true`.
- **label**: Specify the label to filter articles.

### Example 💡

To trigger the workflow manually with specific parameters:

1. Go to the **Actions** tab in your GitHub repository.
2. Select the "Generate and Send Omnivook" workflow.
3. Click on "Run workflow."
4. Enter the desired values for `SINCE`, `archive`, and `label`.
5. Click "Run workflow."

## Features ✨

- **Automated eBook Generation**: The workflow runs daily at 17:30 Argentina time, generating an eBook from the articles saved in Omnivore within the last 24 hours.
- **Manual Triggering**: You can manually trigger the workflow at any time, with configurable options for the start date (`SINCE`) and whether to archive processed articles.
- **Conditional Execution**: The workflow checks if any articles were processed and only sends the eBook and uploads it as an artifact if one was generated.
- **Email Delivery**: The generated eBook is sent directly to a specified Kindle email address.
- **Artifact Storage**: Each generated eBook is also uploaded as an artifact in GitHub, allowing for easy retrieval.


## Setup 🔧

### Secrets 🔐

You need to configure the following GitHub Secrets in your repository:

- **`MAIL_CONNECTION`**: The SMTP connection URL in the format: `smtp://user:password@server:port`.
- **`MAIL_FROM`**: The email address from which the eBook will be sent.
- **`MAIL_TO`**: The Kindle email address where the eBook will be delivered.
