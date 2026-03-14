"""
Add English translations to Volubilis dataset for the rows where only a French 
definition was provided. Use MarianMT to generate translations and put them in
`french-translations.tsv`.
"""

from dict.scripts.paths import RAW_DIR, DB_PATH
import sqlite3
import csv
import re

def add_french_translations():
    with open(RAW_DIR / "french-translations.tsv", "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        next(reader)
        batch = []
        for row in reader:
            # Trim translations where MarianMT hallucinated
            if m := re.search(r"(.+?); (?:\1; ){4,}\1", row["english"]):
                row["english"] = row["english"][:m.group(1).end]
            batch.append((row["english"], int(row["id"])))

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.executemany("UPDATE volubilis SET english = ? WHERE id = ? AND english IS NULL", batch)
        conn.commit()


if __name__ == "__main__":
    add_french_translations()