import csv
import io
import re

# The "Brain": A dictionary mapping categories to regex keywords
CATEGORY_RULES = {
    "Software & Tools": [r"github", r"aws", r"digitalocean", r"vercel", r"adobe", r"jetbrains"],
    "Travel": [r"uber", r"careem", r"lyft", r"train", r"flight", r"taxi"],
    "Hardware & Office": [r"dell", r"amazon", r"logitech", r"apple"],
    "Income": [r"upwork", r"fiverr", r"stripe", r"wire transfer", r"paypal"],
    "Meals & Entertainment": [r"cafe", r"restaurant", r"foodpanda", r"mcdonalds", r"starbucks"]
}

def categorize_transaction(description, amount):
    desc_lower = description.lower()
    amount = float(amount)
    
    for category, patterns in CATEGORY_RULES.items():
        for pattern in patterns:
            if re.search(pattern, desc_lower):
                # Ensure spending isn't accidentally categorized as Income
                if category == "Income" and amount < 0:
                    continue
                return category
                
    return "Needs Review"

def process_statement(file_obj):
    # Decode the uploaded CSV file
    decoded_file = file_obj.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded_file))
    
    results = []
    for row in reader:
        # Assuming standard CSV columns: Date, Description, Amount
        # You can adjust these headers based on the fake CSV you create
        date = row.get("Date", "")
        description = row.get("Description", "")
        amount = row.get("Amount", "0")
        
        category = categorize_transaction(description, amount)
        
        results.append({
            "date": date,
            "description": description,
            "amount": float(amount),
            "category": category,
            "status": "Reviewed" if category != "Needs Review" else "Pending"
        })
    return results