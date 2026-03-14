from dict.scripts.paths import DB_PATH, RAW_DIR
from dict.scripts.phonetic_utils import ipa_to_aua
from dict.scripts.add_phonetic import get_ipa
import sqlite3
import csv

def main():
    with sqlite3.connect(DB_PATH) as conn:
        batch = []
        
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS thai_oov")
        c.execute("""
            CREATE TABLE IF NOT EXISTS thai_oov (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thai TEXT NOT NULL,
                roman TEXT,
                pos TEXT,
                english TEXT,
                note TEXT
            )""")

        with open(RAW_DIR / "thai_oov.tsv", "r") as f:
            reader = csv.DictReader(f, delimiter="\t")
            next(reader)
            for row in reader:
                if not row["roman"]:
                    roman = ipa_to_aua(get_ipa(row["thai"]))
                else:
                    roman = row["roman"]
                batch.append((row["thai"], roman, row["pos"], row["english"], row["note"]))

        c.executemany("""
            INSERT INTO thai_oov (thai, roman, pos, english, note) VALUES (?, ?, ?, ?, ?)
        """, batch)

        conn.commit()


if __name__ == "__main__":
    main()