import re
from typing import Dict, List, Optional, Tuple

CATEGORY_RULES: List[Tuple[str, List[str]]] = [
    (
        "Food & Dining",
        [
            r"\bswiggy\b", r"\bzomato\b", r"\bstarbucks\b", r"\bmcdonald\b", r"\bdomino\b",
            r"\bpizza\b", r"\brestaurant\b", r"\bcafe\b", r"\bbakery\b", r"\bdhaba\b",
            r"\bburger\b", r"\bchai\b", r"\bcoffee\b", r"\bkfc\b", r"\bsubway\b"
        ],
    ),
    (
        "Groceries",
        [
            r"\bzepto\b", r"\bblinkit\b", r"\bbigbasket\b", r"\bbbdaily\b", r"\bdmalt\b",
            r"\bdmart\b", r"\bgrocery\b", r"\bsupermarket\b", r"\bprovisions\b",
            r"\bfresh to home\b", r"\blicious\b", r"\bfruits\b", r"\bvegetables\b"
        ],
    ),
    (
        "Shopping",
        [
            r"\bamazon\b", r"\bflipkart\b", r"\bmyntra\b", r"\bajio\b", r"\bzara\b",
            r"\bh&m\b", r"\bnykaa\b", r"\btata cliq\b", r"\bmeesho\b", r"\bdecathlon\b",
            r"\buniqlo\b", r"\bwestside\b", r"\bshoppers stop\b", r"\belectronics\b"
        ],
    ),
    (
        "Housing",
        [
            r"\brent\b", r"\bmaintenance\b", r"\bmygate\b", r"\bnobroker\b",
            r"\bhousing\b", r"\blandlord\b", r"\bapartment\b", r"\bsociety\b"
        ],
    ),
    (
        "Utilities",
        [
            r"\belectricity\b", r"\btatapower\b", r"\bbescom\b", r"\bmahadiscom\b",
            r"\bairtel\b", r"\bjio\b", r"\bvodafone\b", r"\bvi bill\b", r"\bbroadband\b",
            r"\bact corp\b", r"\bgas bill\b", r"\bindane\b", r"\bwater bill\b", r"\brecharge\b"
        ],
    ),
    (
        "Transport",
        [
            r"\buber\b", r"\bola\b", r"\brapido\b", r"\bmetro\b", r"\bpetrol\b",
            r"\bfuel\b", r"\bindian oil\b", r"\biocl\b", r"\bbpcl\b", r"\bhpcl\b",
            r"\bshell\b", r"\btoll\b", r"\bfastag\b", r"\birctc\b", r"\bindiGo\b"
        ],
    ),
    (
        "Entertainment",
        [
            r"\bnetflix\b", r"\bspotify\b", r"\bhotstar\b", r"\bprime video\b",
            r"\bbookmyshow\b", r"\bpvr\b", r"\binox\b", r"\byoutube\b", r"\bapple\.com/bill\b",
            r"\bsteam\b", r"\bplaystation\b"
        ],
    ),
    (
        "Healthcare",
        [
            r"\bapollo\b", r"\bpharmeasy\b", r"\b1mg\b", r"\bnetmeds\b", r"\bmedplus\b",
            r"\bhospital\b", r"\bpharmacy\b", r"\bclinic\b", r"\bdoctor\b", r"\blab\b",
            r"\bdiagnostic\b", r"\bdental\b"
        ],
    ),
    (
        "Income",
        [
            r"\bsalary\b", r"\bpayroll\b", r"\bstipend\b", r"\bwages\b", r"\binterest credit\b",
            r"\bdividend\b", r"\bbonus\b", r"\bincentive\b"
        ],
    ),
    (
        "Investments",
        [
            r"\bzerodha\b", r"\bgroww\b", r"\bupstox\b", r"\bmutual fund\b", r"\bsip\b",
            r"\bindmoney\b", r"\bcoin\b", r"\bkuvera\b", r"\bnps\b", r"\bppf\b"
        ],
    ),
]


def match_rule_category(narration: str) -> Optional[str]:
    """Test narration text against curated regex category rules."""
    text = narration.lower()
    for cat_name, patterns in CATEGORY_RULES:
        for pat in patterns:
            if re.search(pat, text):
                return cat_name
    return None
