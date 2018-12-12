# Tumblr-To-Blogger Migration Utility
Migrate Posts to Blogger from Tumblr archives

## Requirements
Requires Python 3, Google API for Python, imgurpython and Beautiful Soup
```
pip install --upgrade google-api-python-client imgurpython beautifulsoup4
```

Also requires a blog on Blogger (along with Google API keys) and Tumblr blog archive (you can download this in your blog settings). For convenience, an Imgur API client ID is included in the example config for anonymous uploads, but might become rate limited if many people use it.

## Installation
You can download your API keys from Google as ``client_secrets.json`` - put it in your tumblr_to_blogger directory and set ``blogger_blog_id`` in config.cfg to your Blogger blog's ID.

## Running
Copy config_example.cfg to config.cfg and set blogger_blog_id and tumblr_archive_path (optionally set draft to false to publish immediately)

If you cancel and re-run the script will try to skip posts that have already been submitted to blogger. If something went wrong you can delete ``blog_info.json`` and try again.

```
python migrate.py
```

## What's working
Migration of photo posts from a tumblr zip archive (or extracted archive directory). Photos are uploaded to imgur for now.

Video posts are not yet working and are skipped.
