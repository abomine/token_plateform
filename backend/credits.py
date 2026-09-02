"""Token-to-credit pricing for DeepSeek models.

Platform units: 1 USD = 1,000,000 credits.
DeepSeek R1 list price:
  - input  $0.55 / 1M tokens  -> 0.55 credits / token
  - output $2.19 / 1M tokens  -> 2.19 credits / token
A 20% platform markup is applied to the combined list cost.
"""

from decimal import ROUND_CEILING, Decimal

# Credits charged per token at list price (before markup).
DEEPSEEK_R1_INPUT_CREDITS_PER_TOKEN = Decimal("0.55")
DEEPSEEK_R1_OUTPUT_CREDITS_PER_TOKEN = Decimal("2.19")
PLATFORM_MARKUP = Decimal("1.20")

# Phase 1: all supported DeepSeek chat models share R1 rates.
MODEL_RATES: dict[str, tuple[Decimal, Decimal]] = {
    "deepseek-reasoner": (
        DEEPSEEK_R1_INPUT_CREDITS_PER_TOKEN,
        DEEPSEEK_R1_OUTPUT_CREDITS_PER_TOKEN,
    ),
    "deepseek-r1": (
        DEEPSEEK_R1_INPUT_CREDITS_PER_TOKEN,
        DEEPSEEK_R1_OUTPUT_CREDITS_PER_TOKEN,
    ),
    "deepseek-chat": (
        DEEPSEEK_R1_INPUT_CREDITS_PER_TOKEN,
        DEEPSEEK_R1_OUTPUT_CREDITS_PER_TOKEN,
    ),
}


def calculate_credit_cost(model: str, input_tokens: int, output_tokens: int) -> int:
    """Return integer platform credits to charge for a completed LLM call.

    Unknown models fall back to DeepSeek R1 rates so a new DeepSeek alias
    is still billed. Costs are rounded **up** so the platform never undercharges.
    """
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts must be non-negative")

    input_rate, output_rate = MODEL_RATES.get(
        (model or "").strip().lower(),
        (DEEPSEEK_R1_INPUT_CREDITS_PER_TOKEN, DEEPSEEK_R1_OUTPUT_CREDITS_PER_TOKEN),
    )

    list_cost = (Decimal(input_tokens) * input_rate) + (
        Decimal(output_tokens) * output_rate
    )
    billed = (list_cost * PLATFORM_MARKUP).to_integral_value(rounding=ROUND_CEILING)
    return int(billed)
