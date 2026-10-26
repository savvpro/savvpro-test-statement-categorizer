import csv
import random
from datetime import date, timedelta

def generatedata() -> None:
    """Generate fake statement CSVs for three layouts with specific edge cases."""
    random.seed(42)
    
    startdate = date(2026, 1, 1)
    
    
    transactions: list[tuple[date, str, float]] = []
    
    
    for i in range(4):
        transactions.append((startdate + timedelta(days=i*30), "SHOP RENT KHALID", -85000.0))
        
   
    for i in range(3):
        transactions.append((startdate + timedelta(days=i*5), "IBFT TO CZONE", -150000.0))
        
    
    transactions.append((startdate + timedelta(days=2), "CUSTOMER PAYMENT ALI", 120000.0))
    transactions.append((startdate + timedelta(days=15), "CUSTOMER PAYMENT ALI", 45000.0))
    
    
    transactions.append((startdate + timedelta(days=10), "ADOBE CREATIVE CLOUD", -250000.0))
    transactions.append((startdate + timedelta(days=20), "CUSTOMER PAYMENT OMAR", 95000.0))
    transactions.append((startdate + timedelta(days=22), "REFUND TO OMAR", -95000.0)) # Customer refund
    transactions.append((startdate + timedelta(days=3), "TELEMART PVT LTD", -200000.0)) # Payee paid
    transactions.append((startdate + timedelta(days=8), "RMA REFUND TELEMART", 50000.0)) # RMA refund / Two-way
    transactions.append((startdate + timedelta(days=4), "SELF TRANSFER TO SAVINGS", -50000.0)) # Own-account
    transactions.append((startdate + timedelta(days=5), "DARAZ PK", -12000.0)) # Ambiguous
    transactions.append((startdate + timedelta(days=6), "ATM WITHDRAWAL", -10000.0)) # Ambiguous
    transactions.append((startdate + timedelta(days=7), "TELMART", -45000.0)) # Typo merchant
    transactions.append((startdate + timedelta(days=9), "COD SETTLEMENT TCS", -5000.0)) # Wrong-direction (income keyword, money out)
    transactions.append((startdate + timedelta(days=11), "SMS ALERT CHARGES", -120.0)) # SMS charges
    transactions.append((startdate + timedelta(days=11), "WHT ON CASH", -500.0)) # WHT same day
    
    
    merchantsin = ["COD SETTLEMENT LEOPARDS", "RAAST FROM AHMAD", "CASH DEPOSIT"]
    merchantsout = ["K-ELECTRIC", "PTCL INTERNET", "FACEBK ADS", "TCS COURIER", "SALARY USMAN"]
    
    currentdate = startdate + timedelta(days=25)
    for _ in range(50):
        currentdate += timedelta(days=random.randint(0, 3))
        if random.random() > 0.3:
            transactions.append((currentdate, random.choice(merchantsout), -random.randint(1000, 50000)))
        else:
            transactions.append((currentdate, random.choice(merchantsin), random.randint(5000, 150000)))

   
    transactions.sort(key=lambda x: x[0])
    
    
    transactions.insert(1, transactions[0])

    writelayouta("backend/sampledata/layouta.csv", transactions)
    writelayoutb("backend/sampledata/layoutb.csv", transactions)
    writelayoutc("backend/sampledata/layoutc.csv", transactions)

def writelayouta(filepath: str, transactions: list[tuple[date, str, float]]) -> None:
    balance = 500000.0
    with open(filepath, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Narration", "Chq/Ref No", "Debit", "Credit", "Balance"])
        for i, (dt, desc, amt) in enumerate(transactions):
            if i == 15: # Blank row edge case
                writer.writerow([])
            balance += amt
            debit = f"{abs(amt):.2f}" if amt < 0 else ""
            credit = f"{amt:.2f}" if amt > 0 else ""
            ref = f"REF{random.randint(1000,9999)}"
            writer.writerow([dt.strftime("%d/%m/%Y"), desc, ref, debit, credit, f"{balance:.2f}"])

def writelayoutb(filepath: str, transactions: list[tuple[date, str, float]]) -> None:
    balance = 500000.0
    with open(filepath, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Transaction Date", "Description", "Amount", "Running Balance", "Status"])
        for i, (dt, desc, amt) in enumerate(transactions):
            status = "Pending" if i == 20 else "Posted" # Pending row edge case
            balance += amt
            writer.writerow([dt.strftime("%d-%b-%Y"), desc, f"{amt:.2f}", f"{balance:.2f}", status])

def writelayoutc(filepath: str, transactions: list[tuple[date, str, float]]) -> None:
    balance = 500000.0
    with open(filepath, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Value Date", "Transaction Details", "Withdrawal", "Deposit", "Balance"])
        for dt, desc, amt in transactions:
            balance += amt
            withdrawal = f"{abs(amt):,.2f}" if amt < 0 else ""
            deposit = f"{amt:,.2f}" if amt > 0 else ""
            writer.writerow([dt.strftime("%Y-%m-%d"), desc, withdrawal, deposit, f"{balance:,.2f}"])

if __name__ == "__main__":
    generatedata()
    print("Generated fake statement CSVs in backend/sampledata/")