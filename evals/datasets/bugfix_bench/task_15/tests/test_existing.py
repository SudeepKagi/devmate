from src.slug import slugify
def test_normal():
    assert slugify("Hello World") == "hello-world"
