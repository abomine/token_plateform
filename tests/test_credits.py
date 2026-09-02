from backend.credits import calculate_credit_cost


def test_single_input_token_rounds_up_with_markup():
    # 0.55 * 1.20 = 0.66 -> ceil 1
    assert calculate_credit_cost("deepseek-reasoner", 1, 0) == 1


def test_one_million_tokens_matches_published_r1_rates():
    # $0.55 / 1M input * 1.20 markup = 660_000 credits
    assert calculate_credit_cost("deepseek-r1", 1_000_000, 0) == 660_000
    # $2.19 / 1M output * 1.20 markup = 2_628_000 credits
    assert calculate_credit_cost("deepseek-r1", 0, 1_000_000) == 2_628_000


def test_combined_input_and_output():
    # (100 * 0.55 + 50 * 2.19) * 1.20 = (55 + 109.5) * 1.20 = 197.4 -> ceil 198
    assert calculate_credit_cost("deepseek-chat", 100, 50) == 198


def test_unknown_model_uses_r1_fallback():
    assert calculate_credit_cost("some-new-deepseek-alias", 1_000_000, 0) == 660_000


def test_zero_tokens_is_free():
    assert calculate_credit_cost("deepseek-reasoner", 0, 0) == 0
