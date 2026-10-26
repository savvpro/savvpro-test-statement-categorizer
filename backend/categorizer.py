import re


CATEGORY_RULES = {
    "Software": [
        "ADOBE",
        "CANVA",
        "MICROSOFT",
        "NOTION",
        "FIGMA",
        "GITHUB",
    ],

    "Cloud Services": [
        "AWS",
        "AMAZON WEB SERVICES",
        "DIGITALOCEAN",
        "HEROKU",
        "VERCEL",
        "CLOUDFLARE",
    ],

    "Travel": [
        "UBER",
        "CAREEM",
        "LYFT",
        "AIRBNB",
    ],

    "Food": [
        "CAFE",
        "RESTAURANT",
        "FOODPANDA",
        "MCDONALD",
        "KFC",
    ],

    "Office Supplies": [
        "STAPLES",
        "OFFICE DEPOT",
        "PRINTER",
        "STATIONERY",
    ],

    "Internet & Phone": [
        "PTCL",
        "JAZZ",
        "ZONG",
        "UFONE",
        "INTERNET",
    ],
}


def clean_description(description: str) -> str:
    description = description.upper().strip()

    # Long reference numbers remove karega
    description = re.sub(r"\d{4,}", "", description)

    # Extra spaces remove karega
    description = re.sub(r"\s+", " ", description)

    return description


def categorize_transaction(description: str, amount: float):
    cleaned = clean_description(description)

    # Refund
    if "REFUND" in cleaned:
        return {
            "category": "Refund",
            "confidence": 1.0,
            "needs_review": False,
        }

    # Transfer
    transfer_words = [
        "TRANSFER",
        "SAVINGS",
        "BANK TRANSFER",
    ]

    if any(word in cleaned for word in transfer_words):
        return {
            "category": "Transfer / Not Expense",
            "confidence": 1.0,
            "needs_review": False,
        }

    # Merchant/category rules
    for category, keywords in CATEGORY_RULES.items():

        for keyword in keywords:

            if keyword in cleaned:
                return {
                    "category": category,
                    "confidence": 0.95,
                    "needs_review": False,
                }

    # Agar koi rule match nahi hua
    return {
        "category": "Needs Review",
        "confidence": 0.0,
        "needs_review": True,
    }