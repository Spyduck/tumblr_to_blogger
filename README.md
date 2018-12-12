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
```
python migrate.py
```

## What's working
Migration of photo posts from a tumblr zip archive (or extracted archive directory)

Only photo posts from tumblr get parsed right now.
