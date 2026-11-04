import pytest
from app.ml.categorization.classifier import HybridCategorizer


def test_hybrid_categorizer_rules_and_ml():
    categorizer = HybridCategorizer.get_instance()

    # Rule-based matches
    res1 = categorizer.predict("UPI/DR/SWIGGY/ORDER_BANGALORE")
    assert res1["category"] == "Food & Dining"
    assert res1["source"] == "RULE"
    assert res1["confidence"] >= 0.90

    res2 = categorizer.predict("BLINKIT GROCERY PURCHASE")
    assert res2["category"] == "Groceries"
    assert res2["source"] == "RULE"

    res3 = categorizer.predict("NETFLIX MONTHLY SUBSCRIPTION")
    assert res3["category"] == "Entertainment"
    assert res3["source"] == "RULE"

    # User rule overrides
    user_rules = [
        {
            "match_type": "CONTAINS",
            "match_value": "custom-special-cafe",
            "category_name": "Food & Dining",
        }
    ]
    res_override = categorizer.predict("PAYMENT TO CUSTOM-SPECIAL-CAFE", user_rules=user_rules)
    assert res_override["category"] == "Food & Dining"
    assert res_override["source"] == "USER"
    assert res_override["confidence"] == 1.0
