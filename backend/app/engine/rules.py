import re
from typing import List, Dict, Any, Tuple
from ..models.schemas import CategoryName, TaxDeductibility


CATEGORY_TAXONOMY: Dict[CategoryName, Dict[str, Any]] = {
    CategoryName.SOFTWARE_SUBSCRIPTIONS: {
        "tax_status": TaxDeductibility.FULLY_DEDUCTIBLE,
        "description": "Digital tools, cloud services, and software used directly for client production.",
        "exact_merchants": [
            "adobe creative cloud", "adobe", "figma", "github", "notion", "canva",
            "openai", "chatgpt", "midjourney", "aws", "amazon web services",
            "google workspace", "vercel", "slack", "zoom", "dropbox", "jetbrains",
            "webflow", "envato", "freepik", "shutterstock", "grammarly", "loom",
            "1password", "digitalocean", "cloudflare", "linear", "miro", "atlassian",
            "jira", "sketch", "sublime text", "render", "supabase", "resend", "postman"
        ],
        "keywords": [
            r"\badobe\b", r"\bfigma\b", r"\bgithub\b", r"\bnotion\b", r"\bcanva\b",
            r"\bopenai\b", r"\bchatgpt\b", r"\baws\b", r"\bvercel\b", r"\bslack\b",
            r"\bzoom\.us\b", r"\bdropbox\b", r"\bwebflow\b", r"\bcloud\b", r"\bhosting\b",
            r"\bsubscription\b", r"\bsaas\b", r"\bdomain\b", r"\bnamecheap\b", r"\bgodaddy\b"
        ]
    },

    CategoryName.OFFICE_EQUIPMENT: {
        "tax_status": TaxDeductibility.FULLY_DEDUCTIBLE,
        "description": "Hardware, monitors, desk accessories, and production electronics.",
        "exact_merchants": [
            "apple store", "best buy", "micro center", "b&h photo", "dell",
            "logitech", "office depot", "staples", "ikea", "keychron",
            "wacom", "elgato", "anker", "caldigit"
        ],
        "keywords": [
            r"\bapple\s*store\b", r"\bbest\s*buy\b", r"\bmicro\s*center\b", r"\bb&h\s*photo\b",
            r"\bequipment\b", r"\bhardware\b", r"\bmonitor\b", r"\blaptop\b", r"\bkeyboard\b",
            r"\belectronics\b", r"\boffice\s*depot\b", r"\bstaples\b"
        ]
    },

    CategoryName.TRAVEL_RIDESHARE: {
        "tax_status": TaxDeductibility.FULLY_DEDUCTIBLE,
        "description": "Transportation, flights, and rideshare for business/client visits.",
        "exact_merchants": [
            "uber", "lyft", "delta air lines", "delta", "united airlines",
            "american airlines", "amtrak", "booking.com", "expedia", "hertz",
            "enterprise rent-a-car", "marriott", "hilton", "hyatt", "airbnb"
        ],
        "keywords": [
            r"\buber\b", r"\blyft\b", r"\brideshare\b", r"\btaxi\b", r"\bcab\b",
            r"\bairline\b", r"\bflight\b", r"\bairways\b", r"\bamtrak\b", r"\bhotel\b",
            r"\btransit\b", r"\bparking\b", r"\btoll\b"
        ]
    },

    CategoryName.MEALS_ENTERTAINMENT: {
        "tax_status": TaxDeductibility.PARTIALLY_DEDUCTIBLE,
        "description": "Business meals with clients or while travelling (Subject to 50% IRS deduction limit).",
        "exact_merchants": [
            "starbucks", "starbucks coffee", "blue bottle coffee", "dunkin",
            "doordash", "uber eats", "grubhub", "pret a manger", "panera bread",
            "chipotle", "sweetgreen", "shake shack", "peet's coffee"
        ],
        "keywords": [
            r"\bstarbucks\b", r"\bdoordash\b", r"\buber\s*eats\b", r"\bgrubhub\b",
            r"\bblue\s*bottle\b", r"\bpret\s*a\s*manger\b", r"\bpanera\b", r"\bchipotle\b"
        ],
        # Ambiguous weak keywords that require verification (assigned lower weight)
        "weak_keywords": [
            r"\bcafe\b", r"\bcoffee\b", r"\bdiner\b", r"\bbistro\b", r"\brestaurant\b", r"\bbakery\b"
        ]
    },

    CategoryName.MARKETING_ADVERTISING: {
        "tax_status": TaxDeductibility.FULLY_DEDUCTIBLE,
        "description": "Client acquisition, sponsored ads, email marketing, and portfolio promotion.",
        "exact_merchants": [
            "google ads", "meta ads", "facebook ads", "linkedin ads",
            "twitter ads", "x ads", "mailchimp", "convertkit", "buffer",
            "hootsuite", "tiktok ads", "pinterest ads"
        ],
        "keywords": [
            r"\bgoogle\s*ads?\b", r"\bmeta\s*ads?\b", r"\bfacebook\s*ads?\b",
            r"\blinkedin\s*ads?\b", r"\badvertis\w*\b", r"\bmarketing\b",
            r"\bpromotions?\b", r"\bmailchimp\b", r"\bnewsletter\b"
        ]
    },

    CategoryName.PROFESSIONAL_FEES: {
        "tax_status": TaxDeductibility.FULLY_DEDUCTIBLE,
        "description": "Payment platform processing fees, freelancing platform fees, legal, and accounting.",
        "exact_merchants": [
            "upwork escrow", "upwork service fee", "fiverr fee", "fiverr",
            "stripe fee", "paypal merchant fee", "legalzoom", "turbotax",
            "quickbooks", "xero", "gusto", "deel", "bank wire fee"
        ],
        "keywords": [
            r"\bupwork\b", r"\bfiverr\b", r"\bprocessing\s*fee\b", r"\bmerchant\s*fee\b",
            r"\bwire\s*fee\b", r"\bservice\s*fee\b", r"\blegal\b", r"\baccounting\b",
            r"\bcpa\b", r"\btax\s*prep\b", r"\bconsulting\s*fee\b"
        ]
    },

    CategoryName.UTILITIES_INTERNET: {
        "tax_status": TaxDeductibility.FULLY_DEDUCTIBLE,
        "description": "High-speed broadband and mobile connectivity required for freelance work.",
        "exact_merchants": [
            "comcast", "xfinity", "verizon", "at&t", "spectrum",
            "t-mobile", "google fiber", "cox communications"
        ],
        "keywords": [
            r"\bcomcast\b", r"\bxfinity\b", r"\bverizon\b", r"\bat&t\b", r"\bspectrum\b",
            r"\bt-mobile\b", r"\bbroadband\b", r"\binternet\b", r"\bfiber\b"
        ]
    }
}

INTERNAL_TRANSFER_PATTERNS = [
    r"\btransfer\s+to\s+savings\b",
    r"\btransfer\s+from\s+checking\b",
    r"\btransfer\s+to\s+checking\b",
    r"\bautopay\s+(?:credit\s*card|pymt)\b",
    r"\bcredit\s*card\s*payment\b",
    r"\bpayment\s*-\s*thank\s*you\b",
    r"\bthank\s*you\s*payment\b",
    r"\batm\s+cash\s+withdrawal\b",
    r"\bowner\s*draw\b",
    r"\bwire\s+transfer\s+to\s+personal\b",
    r"\bself\s*transfer\b",
    r"\bzelle\s+transfer\s+to\s+self\b"
]

INCOME_PATTERNS = [
    r"\bclient\s*invoice\b",
    r"\bclient\s*payment\b",
    r"\bwire\s*transfer\s*(?:incoming|credit)\b",
    r"\bupwork\s*(?:withdrawal|payout|earnings)\b",
    r"\bstripe\s*payout\b",
    r"\bach\s*credit\b",
    r"\bdeposit\b",
    r"\bpayroll\s*direct\s*deposit\b",
    r"\bconsulting\s*income\b",
    r"\bfiverr\s*payout\b"
]

REFUND_KEYWORDS = [
    r"\brefund\b",
    r"\breturn\b",
    r"\bcredit\s*adjustment\b",
    r"\bchargeback\s*reversal\b",
    r"\breimbursement\b"
]
