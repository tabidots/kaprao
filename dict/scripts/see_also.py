import sqlite3
import json
from dict.scripts.paths import DB_PATH
from dict.scripts.phonetic_utils import romanize_from_volubilis


with sqlite3.connect(DB_PATH) as conn:
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS see_also")
    c.execute("""
        CREATE TABLE IF NOT EXISTS see_also (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            headword_id INTEGER NOT NULL,
            thai TEXT NOT NULL,
            toneless TEXT,
            vphon TEXT,
            roman TEXT
        )
    """)

    batch = []
    c.execute("""
        SELECT id, thai, roman, see_also FROM volubilis 
        WHERE see_also IS NOT NULL
    """)
    for (headword_id, thai, roman, see_also_raw) in c.fetchall():
        see_also = json.loads(see_also_raw)
        if not see_also.get("thai", None):
            continue
        batch.append((headword_id,
                      see_also["thai"],
                      see_also.get("toneless", None),
                      see_also.get("vphon", None),))
    
    c.executemany("""
        INSERT INTO see_also (headword_id, thai, toneless, vphon)
        VALUES (?, ?, ?, ?)
    """, batch)
    conn.commit()

    print("Filling in romanizations for referents that exist in the base dictionary...")
    c.execute("""
        UPDATE see_also
        SET roman = v.roman
        FROM volubilis v
        WHERE see_also.thai = v.thai
    """)
    conn.commit()

    print("Filling in romanizations for referents that exist in Wiktionary...")
    c.execute("""
        UPDATE see_also
        SET roman = thw.roman
        FROM th_wiktionary thw
        WHERE see_also.thai = thw.word AND see_also.roman IS NULL
    """)
    conn.commit()

    print("Filling in romanizations for referents that have a `vphon` value...")
    c.execute("""
        SELECT id, thai, vphon FROM see_also
        WHERE roman IS NULL AND vphon IS NOT NULL
    """)
    batch = []
    for (id, thai, vphon) in c.fetchall():
        roman = romanize_from_volubilis(vphon, thai)
        batch.append((roman, id))
    c.executemany("""
        UPDATE see_also
        SET roman = ?
        WHERE id = ?
    """, batch)
    conn.commit()

    batch = []
    c.execute("""
        SELECT headword_id, thai, roman FROM see_also
    """)
    results = c.fetchall()
    for (headword_id, thai, roman) in results:
        payload = { "thai": thai }
        if roman:
            payload["roman"] = roman
        batch.append((json.dumps(payload, ensure_ascii=False), headword_id))

    c.executemany("""
        UPDATE volubilis
        SET see_also = ?
        WHERE id = ?
    """, batch)
    conn.commit()

