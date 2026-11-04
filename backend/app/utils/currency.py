# app/utils/currency.py

def format_bdt(val: int | float | None) -> str:
    if val is None:
        return "৳0"
    amt = int(val)
    # Bangladeshi / South Asian numbering formatting: e.g. 1,50,000 or standard commas
    # We can format with standard thousand separators: ৳150,000
    return f"৳{amt:,}"
