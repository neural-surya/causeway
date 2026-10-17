from causeway.embed import DIM, embed


def test_embed_is_deterministic_and_normalised():
    a = embed("payments retry timeout")
    assert a == embed("payments retry timeout")
    assert len(a) == DIM
    assert abs(sum(x * x for x in a) - 1.0) < 1e-9


def test_shared_words_are_closer_than_unrelated():
    dot = lambda u, v: sum(x * y for x, y in zip(u, v))
    q = embed("payments gateway retry timeout")
    assert dot(q, embed("retry policy timeout in payments")) > dot(q, embed("inventory shelf label printer"))
