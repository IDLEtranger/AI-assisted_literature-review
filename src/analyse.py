import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

INPUT_PATH = Path("data/included_records.csv")
df = pd.read_csv(INPUT_PATH)

annual = df.groupby("year").size().reset_index(name="n_publications")

plt.figure(figsize=(8, 4))
plt.plot(annual["year"], annual["n_publications"], marker="o")
plt.xlabel("Publication year")
plt.ylabel("Number of included records")
plt.title("Annual publication trend")
plt.tight_layout()
plt.show()