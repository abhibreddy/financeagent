"""
Generates synthetic invoice data with embedded fraud patterns:
- Exact duplicates (same vendor + amount + date)
- Near-duplicates (same amount, slightly different date)
- Split billing (many small invoices from one vendor in a week)
- Round-number clustering (amounts just below $10k approval threshold)
- Ghost vendors (vendor appears only in flagged invoices)
"""
import pandas as pd
import random

random.seed(42)

VENDORS = [
    "Apex Office Supplies", "Metro Consulting LLC", "CloudHost Pro",
    "DataSec Partners", "TechFix Services", "GreenLeaf Catering",
    "Premier Logistics", "Sigma Analytics", "BlueStar Events",
]

GHOST_VENDOR = "Phantom Solutions LLC"
CATEGORIES   = ["IT Services", "Office Supplies", "Consulting", "Logistics", "Catering", "Software"]
DEPARTMENTS  = ["Finance", "Operations", "IT", "HR", "Marketing"]

rows = []
invoice_num = 1000


def make_invoice(vendor, amount, date, dept, category, is_dup=False, is_split=False,
                 is_ghost=False, is_threshold=False, fraud_type=None):
    global invoice_num
    row = {
        "invoice_id":    f"INV-{invoice_num:05d}",
        "vendor":        vendor,
        "amount":        round(amount, 2),
        "date":          date,
        "department":    dept,
        "category":      category,
        "approver":      random.choice(["J.Smith", "A.Patel", "M.Chen", "R.Kumar"]),
        "is_duplicate":  is_dup,
        "is_split":      is_split,
        "is_ghost":      is_ghost,
        "is_threshold":  is_threshold,
        "fraud_type":    fraud_type or "",
    }
    invoice_num += 1
    return row


# Normal invoices
dates = pd.date_range("2024-01-01", periods=90).strftime("%Y-%m-%d").tolist()
for _ in range(80):
    rows.append(make_invoice(
        vendor=random.choice(VENDORS),
        amount=round(random.uniform(200, 8000), 2),
        date=random.choice(dates),
        dept=random.choice(DEPARTMENTS),
        category=random.choice(CATEGORIES),
    ))

# Fraud Pattern 1: Exact duplicates
dup_invoice = make_invoice("Metro Consulting LLC", 4750.00, "2024-02-14",
                           "Finance", "Consulting")
rows.append(dup_invoice)
dup_copy = dup_invoice.copy()
dup_copy["invoice_id"] = f"INV-{invoice_num:05d}"
dup_copy["is_duplicate"] = True
dup_copy["fraud_type"] = "exact_duplicate"
invoice_num += 1
rows.append(dup_copy)

# Fraud Pattern 2: Near-duplicate (1-day date drift)
rows.append(make_invoice("Apex Office Supplies", 3200.00, "2024-03-05",
                         "Operations", "Office Supplies"))
rows.append(make_invoice("Apex Office Supplies", 3200.00, "2024-03-06",
                         "Operations", "Office Supplies",
                         is_dup=True, fraud_type="near_duplicate"))

# Fraud Pattern 3: Split billing (8 invoices in one week)
for i in range(8):
    d = pd.Timestamp("2024-04-01") + pd.Timedelta(days=i % 5)
    rows.append(make_invoice("Sigma Analytics", round(random.uniform(1100, 1300), 2),
                             d.strftime("%Y-%m-%d"), "IT", "IT Services",
                             is_split=True, fraud_type="split_billing"))

# Fraud Pattern 4: Just-below-threshold invoices
for _ in range(5):
    rows.append(make_invoice(
        vendor=random.choice(VENDORS),
        amount=round(random.uniform(9700, 9999), 2),
        date=random.choice(dates[:30]),
        dept="Finance", category="Consulting",
        is_threshold=True, fraud_type="threshold_avoidance",
    ))

# Fraud Pattern 5: Ghost vendor
for _ in range(4):
    rows.append(make_invoice(
        vendor=GHOST_VENDOR,
        amount=round(random.uniform(5000, 15000), 2),
        date=random.choice(dates[60:]),
        dept="Operations", category="Consulting",
        is_ghost=True, fraud_type="ghost_vendor",
    ))

df = pd.DataFrame(rows)
df.to_csv("synthetictables/invoices.csv", index=False)
print(f"Generated {len(df)} invoices ({df['fraud_type'].ne('').sum()} flagged)")
