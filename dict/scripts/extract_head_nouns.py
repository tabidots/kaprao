import sqlite3
from dict.scripts.paths import DB_PATH, RAW_DIR
import re
from collections import Counter

def main():
    head_nouns = Counter()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT segmentation FROM th_wikipedia WHERE segmentation LIKE '[%'")
        for (segmentation,) in c.fetchall():
            head_noun = re.match(r"\[([^<>\[\]]*?)\]", segmentation).group(1)
            head_nouns[head_noun] += 1

        c.execute("CREATE TEMP TABLE head_nouns (head_noun TEXT PRIMARY KEY, count INTEGER)")
        c.executemany("INSERT INTO head_nouns (head_noun, count) VALUES (?, ?)", head_nouns.items())
        
        c.execute("""
            SELECT hn.head_noun, 
                   hn.count, 
                   GROUP_CONCAT(v.english, '; ' ORDER BY v.id) AS english,
                   GROUP_CONCAT(tr.translit_of, '; ') AS translit_of
            FROM head_nouns hn
            LEFT JOIN volubilis v ON hn.head_noun = v.thai
            LEFT JOIN translit tr ON hn.head_noun = tr.thai
            GROUP BY hn.head_noun
            ORDER BY hn.count DESC
        """)

        with open(RAW_DIR / "head_nouns.tsv", "w") as f:
            f.write("head_noun\tcount\tenglish\n")
            for (head_noun, count, english, translit_of) in c.fetchall():
                if count <= 5:
                    break
                out = []
                if translit_of:
                    for t in translit_of.split("; "):
                        if t and t not in out:
                            out.append(t)
                if english:
                    for e in english.split("; "):
                        if e and e not in out:
                            out.append(e)
                f.write(f"{head_noun}\t{count}\t{'; '.join(out)}\n")


if __name__ == "__main__":
    main()