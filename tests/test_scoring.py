from backend.services.scoring import calculate_score


def test_calculate_score_rewards_relevant_edit_material():
    score = calculate_score(
        title="Jon Snow cinematic battle 4k raw footage",
        query="Jon Snow",
        views=250_000,
    )
    assert score > 0


def test_calculate_score_never_returns_negative():
    score = calculate_score(
        title="reaction podcast review tutorial stream",
        query="totally-unrelated",
        views=0,
    )
    assert score >= 0
