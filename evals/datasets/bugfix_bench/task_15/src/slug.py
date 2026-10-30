import re

def slugify(text):
    text = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", text)
    # BUG: wrong slice or missing strip('-')
    if slug.startswith("-"):
        slug = slug[1:]
    return slug
