"""Knowledge the brain uses: patterns, merchants and thresholds.

Kept as plain data so a reviewer (or the business) can read and extend it
without touching the decision logic in engine.py.
"""

import re

# Confidence below this goes to Needs Review instead of being guessed.
REVIEW_THRESHOLD = 0.75

# A fuel-brand charge this small is probably a snack from the shop, not gas.
FUEL_MIN_AMOUNT = 15

# Rideshare / delivery platforms the driver earns from.
PLATFORMS = ("UBER", "LYFT", "DOORDASH", "GRUBHUB", "INSTACART", "UBER EATS", "SPARK", "SHIPT", "AMAZON FLEX")

TRANSFER = re.compile(
    r"\b(TRANSFER|XFER)\b.*\b(SAVINGS|CHECKING|TO|FROM)\b|\bONLINE BANKING TRANSFER\b|\bINTERNAL TRANSFER\b", re.I
)
# Paying off the card. Not "T-MOBILE AUTOPAY": that is a phone bill on autopay.
CARD_PAYMENT = re.compile(
    r"PAYMENT\s*(-\s*)?THANK\s*YOU|CREDIT CARD PAYMENT|CARDMEMBER PAYMENT|"
    r"(AUTOPAY|ONLINE)\s+PAYMENT\s+(TO\s+)?(CARD|VISA|MASTERCARD|AMEX|DISCOVER|CHASE|CITI|CAPITAL ONE)",
    re.I,
)
# Orders the driver placed as a customer ("DD *" is DoorDash's card prefix).
FOOD_ORDER = re.compile(r"^\s*DD\s*\*|UBER\s*\*?\s*EATS|DOORDASH\s*\*|GRUBHUB\s*\*|POSTMATES", re.I)
# Words that mark the driver side of a platform (earnings, not orders).
DRIVER_SIDE = re.compile(r"\b(DASHER|DRIVER|COURIER|SHOPPER|PAYOUT|EARNINGS|DIRECT DEP|DEPOSIT)\b", re.I)
REFUND = re.compile(r"\b(REFUND|RETURN|REVERSAL|REVERSED|CREDIT VOUCHER|CHARGEBACK|ADJUSTMENT CREDIT)\b", re.I)
PAYOUT = re.compile(r"\b(PAYOUT|PAY OUT|EARNINGS|DIRECT DEP|DIR DEP|DEPOSIT|INSTANT PAY|DAILY PAY|FAST PAY|PAYMENTS?)\b", re.I)
BONUS = re.compile(r"\b(TIP|TIPS|BONUS|QUEST|PROMOTION|INCENTIVE)\b", re.I)
PEER_TO_PEER = re.compile(r"\b(ZELLE|VENMO|CASH APP|CASHAPP|APPLE CASH)\b", re.I)
BANK_FEE = re.compile(r"\b(OVERDRAFT|NSF|MONTHLY SERVICE FEE|MAINTENANCE FEE|FOREIGN TRANSACTION FEE|ATM FEE|LATE FEE)\b", re.I)
INTEREST = re.compile(r"\b(INTEREST CHARGE|PURCHASE INTEREST|FINANCE CHARGE)\b", re.I)

# Debit merchants: (pattern, category, confidence, label).
# Order matters: the first match wins, so specific patterns come first.
MERCHANTS: list[tuple[re.Pattern, str, float, str]] = [
    (re.compile(r"UBER\s*\*?\s*EATS|DOORDASH|GRUBHUB|POSTMATES", re.I), "Meals (Personal)", 0.85, "food delivery order"),
    (re.compile(r"UBER\s*\*?\s*(TRIP|RIDE)|LYFT\s*\*?\s*(RIDE|TRIP)", re.I), "Personal", 0.8, "ride taken as a passenger"),
    (re.compile(r"TESLA SUPERCHARG|ELECTRIFY AMERICA|CHARGEPOINT|EVGO", re.I), "EV Charging", 0.95, "EV charging network"),
    (re.compile(r"\b(SHELL|EXXON|EXXONMOBIL|MOBIL|CHEVRON|TEXACO|VALERO|SUNOCO|CITGO|MARATHON|PHILLIPS 66|CONOCO|BP|"
                r"ARCO|QT|QUIKTRIP|RACETRAC|RACEWAY|MURPHY|WAWA|SHEETZ|CASEYS|LOVES|PILOT|BUCEES|BUC-EES|SPEEDWAY)\b", re.I),
     "Fuel", 0.9, "fuel station"),
    (re.compile(r"COSTCO GAS|SAMS CLUB FUEL|KROGER FUEL|SAFEWAY FUEL", re.I), "Fuel", 0.95, "warehouse fuel pump"),
    (re.compile(r"CAR WASH|AUTO SPA|MISTER CAR|TOMMYS EXPRESS|ZIPS|QUICK QUACK|AUTOBELL", re.I), "Car Wash", 0.95, "car wash"),
    (re.compile(r"JIFFY LUBE|VALVOLINE|TAKE 5|FIRESTONE|PEP BOYS|DISCOUNT TIRE|AUTOZONE|O\s*REILLY|ADVANCE AUTO|"
                r"NAPA|MIDAS|MEINEKE|GOODYEAR|SAFELITE|NTB", re.I), "Vehicle Maintenance", 0.95, "auto service or parts"),
    (re.compile(r"E-?Z ?PASS|SUNPASS|TXTAG|NTTA|FASTRAK|I-?PASS|PEACH PASS|PIKEPASS|TOLL", re.I), "Tolls & Parking", 0.95, "toll account"),
    (re.compile(r"PARKMOBILE|SPOTHERO|PAYBYPHONE|LAZ PARKING|SP\+|PARKING|PARK METER", re.I), "Tolls & Parking", 0.9, "parking"),
    (re.compile(r"VERIZON|T-?MOBILE|AT&T|ATT\*|SPRINT|CRICKET|MINT MOBILE|VISIBLE|BOOST MOBILE|METRO BY", re.I),
     "Phone & Data", 0.9, "phone carrier"),
    (re.compile(r"GEICO|PROGRESSIVE|STATE FARM|ALLSTATE|LIBERTY MUTUAL|USAA INS|FARMERS INS|ROOT INS", re.I),
     "Vehicle Insurance", 0.9, "auto insurer"),
    (re.compile(r"GRIDWISE|STRIDE|EVERLANCE|MILEIQ|QUICKBOOKS|TURBOTAX|CHECKR|DMV|DEPT OF MOTOR|VEHICLE REG", re.I),
     "Business Apps & Fees", 0.9, "driver app or licensing"),
    (re.compile(r"PHONE MOUNT|DASH CAM|CAR CHARGER|INSULATED BAG|HOT BAG", re.I), "Driver Supplies", 0.85, "driver gear"),
    (re.compile(r"MCDONALD|STARBUCKS|CHIPOTLE|TACO BELL|WENDY|BURGER KING|CHICK-?FIL-?A|SUBWAY|DUNKIN|SONIC|"
                r"PANERA|DOMINOS|PIZZA HUT|WHATABURGER|IN-N-OUT|RESTAURANT|CAFE|GRILL", re.I),
     "Meals (Personal)", 0.85, "restaurant"),
    (re.compile(r"NETFLIX|SPOTIFY|HULU|DISNEY|HBO|APPLE\.COM/BILL|PLAYSTATION|XBOX|PLANET FITNESS|LA FITNESS", re.I),
     "Personal", 0.9, "personal subscription"),
    (re.compile(r"WALMART|TARGET|KROGER|HEB|PUBLIX|ALDI|SAFEWAY|WHOLE FOODS|TRADER JOE", re.I),
     "Personal", 0.8, "groceries or household"),
]

# Merchants that sell both business and personal things: never guess.
AMBIGUOUS = re.compile(r"AMAZON|AMZN|BEST BUY|COSTCO WHSE|SAMS CLUB|7-?ELEVEN|CIRCLE K|EBAY|ETSY", re.I)
