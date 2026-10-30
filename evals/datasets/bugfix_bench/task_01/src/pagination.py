def paginate(items, page=1, page_size=10):
    if page < 1 or page_size < 1:
        return []
    start = (page - 1) * page_size
    end = start + page_size + 1  # BUG: extra +1
    return items[start:end]
