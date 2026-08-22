

import pandas as pd

# Show full untruncated output for all 252 fields
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.max_colwidth", None)

try:
    df_expected = pd.read_csv("Unihack_ Expected Output - Delivery Format.csv")
    df_actual = pd.read_csv("output_enriched.csv")
except Exception:
    df_expected = pd.read_csv("backend/Unihack_ Expected Output - Delivery Format.csv")
    df_actual = pd.read_csv("backend/output_enriched.csv")

# Match by MPN (PDSH4816AF)
exp_row = df_expected[df_expected["Mfg_Part_Num"] == "PDSH4816AF"].iloc[0]
act_row = df_actual[df_actual["Mfg_Part_Num"] == "PDSH4816AF"].iloc[0]

comp = exp_row.compare(act_row)
print("=== FULL UNTRUNCATED COMPARISON FOR PDSH4816AF (252 Fields) ===")
print(comp)
