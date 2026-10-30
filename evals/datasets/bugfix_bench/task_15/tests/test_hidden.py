from src.slug import slugify
def test_hidden_both_ends():
    assert slugify("---Test Title---") == "test-title"
def test_hidden_symbols():
    assert slugify("Special @#$ Chars") == "special-chars"
