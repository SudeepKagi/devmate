from src.slug import slugify
def test_trailing_punctuation():
    assert slugify("Hello World!") == "hello-world"
