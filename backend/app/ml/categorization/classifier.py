import re
from typing import Any, Dict, List, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from app.ml.categorization.rules import match_rule_category


# Synthetic bootstrapping dataset for ML classifier initialization
BOOTSTRAP_TRAINING_DATA = [
    ("swiggy food delivery order 4821", "Food & Dining"),
    ("zomato online meal payment bangalore", "Food & Dining"),
    ("starbucks coffee bandra west", "Food & Dining"),
    ("mcdonalds burger meal drive thru", "Food & Dining"),
    ("dominos pizza electronic city", "Food & Dining"),
    ("subway sandwich and drinks", "Food & Dining"),
    ("chai point hot beverage", "Food & Dining"),
    ("zepto grocery quick commerce 10 mins", "Groceries"),
    ("blinkit milk bread butter vegetables", "Groceries"),
    ("bigbasket weekly groceries order", "Groceries"),
    ("nature basket fresh provisions", "Groceries"),
    ("dmart super center store purchase", "Groceries"),
    ("amazon marketplace retail purchase", "Shopping"),
    ("flipkart internet private limited", "Shopping"),
    ("myntra fashion apparel shopping", "Shopping"),
    ("zara retail clothing mall", "Shopping"),
    ("h&m fashion store inorbit", "Shopping"),
    ("ajio trends digital order", "Shopping"),
    ("rent payment for flat 402 green acres", "Housing"),
    ("society monthly maintenance charges", "Housing"),
    ("mygate society club house fees", "Housing"),
    ("nobroker house deposit balance", "Housing"),
    ("tatapower electricity bill payment", "Utilities"),
    ("bescom power electricity online", "Utilities"),
    ("airtel broadband fiber monthly recharge", "Utilities"),
    ("jio prepaid mobile recharge 4g", "Utilities"),
    ("indane lpg domestic cylinder refill", "Utilities"),
    ("uber trip ride airport to home", "Transport"),
    ("ola cabs city taxi ride", "Transport"),
    ("rapido bike taxi commute", "Transport"),
    ("metro card smart card recharge", "Transport"),
    ("indian oil petrol pump fuel filling", "Transport"),
    ("bharat petroleum fuel bunk", "Transport"),
    ("fastag toll plaza automated debit", "Transport"),
    ("netflix entertainment streaming subscription", "Entertainment"),
    ("spotify premium music service", "Entertainment"),
    ("disney hotstar annual vip plan", "Entertainment"),
    ("bookmyshow movie cinema tickets pvr", "Entertainment"),
    ("pvr cinemas popcorn and tickets", "Entertainment"),
    ("apollo pharmacy medicines and tablets", "Healthcare"),
    ("1mg tata online prescription delivery", "Healthcare"),
    ("pharmeasy healthcare medicines order", "Healthcare"),
    ("dr batra clinic consultation fee", "Healthcare"),
    ("lal path labs diagnostic blood test", "Healthcare"),
    ("salary credit acme technologies private limited", "Income"),
    ("monthly payroll salary transfer credited", "Income"),
    ("consulting professional fees received", "Income"),
    ("zerodha broking limited fund transfer", "Investments"),
    ("groww pay investment mutual fund sip", "Investments"),
    ("upstox securities equity investment", "Investments"),
]


class HybridCategorizer:
    """Hybrid transaction categorization engine combining rules and Scikit-learn ML."""

    _instance = None

    def __init__(self):
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, lowercase=True)
        self.classifier = LogisticRegression(max_iter=500, C=1.0)
        self._is_trained = False
        self._train_bootstrap_model()

    @classmethod
    def get_instance(cls) -> "HybridCategorizer":
        if cls._instance is None:
            cls._instance = HybridCategorizer()
        return cls._instance

    def _train_bootstrap_model(self):
        texts = [x[0] for x in BOOTSTRAP_TRAINING_DATA]
        labels = [x[1] for x in BOOTSTRAP_TRAINING_DATA]

        x_vec = self.vectorizer.fit_transform(texts)
        self.classifier.fit(x_vec, labels)
        self._is_trained = True

    def predict(
        self,
        narration: str,
        user_rules: Optional[List[Dict[str, str]]] = None,
        confidence_threshold: float = 0.60
    ) -> Dict[str, Any]:
        """Categorize a transaction narration with source attribution and confidence."""
        cleaned = narration.strip()

        # Step 1: User custom override rules
        if user_rules:
            for rule in user_rules:
                m_type = rule.get("match_type", "CONTAINS")
                m_val = rule.get("match_value", "").lower()
                target_cat = rule.get("category_name", "Other")

                if m_type == "EXACT" and cleaned.lower() == m_val:
                    return {
                        "category": target_cat,
                        "confidence": 1.0,
                        "source": "USER",
                        "needs_review": False,
                    }
                elif m_type == "CONTAINS" and m_val in cleaned.lower():
                    return {
                        "category": target_cat,
                        "confidence": 1.0,
                        "source": "USER",
                        "needs_review": False,
                    }
                elif m_type == "REGEX":
                    if re.search(m_val, cleaned.lower()):
                        return {
                            "category": target_cat,
                            "confidence": 1.0,
                            "source": "USER",
                            "needs_review": False,
                        }

        # Step 2: System regex rules
        rule_match = match_rule_category(cleaned)
        if rule_match:
            return {
                "category": rule_match,
                "confidence": 0.95,
                "source": "RULE",
                "needs_review": False,
            }

        # Step 3: Scikit-learn TF-IDF + Logistic Regression
        if self._is_trained:
            vec = self.vectorizer.transform([cleaned])
            probs = self.classifier.predict_proba(vec)[0]
            max_prob_idx = probs.argmax()
            predicted_cat = self.classifier.classes_[max_prob_idx]
            conf = float(probs[max_prob_idx])

            needs_review = conf < confidence_threshold
            return {
                "category": predicted_cat if not needs_review else "Other",
                "confidence": round(conf, 3),
                "source": "ML",
                "needs_review": needs_review,
            }

        return {
            "category": "Other",
            "confidence": 0.0,
            "source": "RULE",
            "needs_review": True,
        }
