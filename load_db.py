import sqlite3
import pandas as pd

df = pd.read_csv("data/sfc_short_positions.csv")
conn = sqlite3.connect("shorts.db")
df.to_sql("short_positions", conn, if_exists="replace", index=False)
conn.close()
print(f"Loaded {len(df)} rows)")