import sqlite3
import json
import sys
import re
from collections import defaultdict


def get_classifier_romans(c):
    classifier_lookup = {}

    c.execute("""
        SELECT v1.classifier AS cl, v2.roman
        FROM volubilis v1
        LEFT JOIN
            volubilis v2 ON v2.thai = cl AND v2.pos <> 'n. prop.'
        WHERE cl IS NOT NULL AND cl NOT LIKE '%;%' AND v2.roman IS NOT NULL
        GROUP BY cl
              
        UNION ALL
              
        SELECT thw.classifier AS cl, v.roman
        FROM th_wiktionary thw
        LEFT JOIN
            volubilis v ON v.thai = cl AND v.pos <> 'n. prop.'
        WHERE cl IS NOT NULL AND cl NOT LIKE '%;%' AND v.roman IS NOT NULL
        GROUP BY cl
    """)
    classifier_lookup = {cl: roman for cl, roman in c.fetchall()}
    c.execute("""
        SELECT DISTINCT classifier FROM volubilis
        WHERE classifier LIKE '%;%'
              
        UNION ALL
              
        SELECT DISTINCT classifier FROM th_wiktionary
        WHERE classifier LIKE '%;%'
    """)
    for (cl,) in c.fetchall():
        for single_cl in cl.split(" ; "):
            c.execute("""
                SELECT roman FROM volubilis 
                WHERE thai = ? AND pos <> 'n. prop.'
            """, (single_cl,))
            result = c.fetchone()
            if not result: 
                continue
            classifier_lookup[cl] = result[0]

    return classifier_lookup


def get_wiktionary_phrases(cur):
    cur.execute("""
        SELECT thw.word
        FROM th_wiktionary thw
        JOIN volubilis v ON v.thai = thw.word
        WHERE thw.pos = 'phrase';
    """)
    return {x for (x,) in cur.fetchall()}


def main(db_path, out_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    CLASSIFIERS = get_classifier_romans(cur)
    WIKTIONARY_PHRASES = get_wiktionary_phrases(cur)

    # Export base dictionary data

    cur.execute("""
        SELECT v.thai, variants, see_also, v.roman, 
               v.english, v.pos AS pos, v.classifier as cl,
               v.note AS tags, NULL as is_compound -- w.is_compound as is_compound
        FROM volubilis v
        -- LEFT JOIN th_wiktionary w ON w.word = v.thai
        -- GROUP BY v.id  -- prevent the JOIN from duplicating rows

        UNION ALL

        SELECT o.thai AS thai, NULL, NULL, roman, 
               o.english, o.pos AS pos, NULL,
               NULL, NULL as is_compound
        FROM thai_oov o
                
        UNION ALL
                
        SELECT thw.word as thai, NULL, NULL, thw.roman, 
               CASE 
                    WHEN thw.english IS NOT NULL THEN thw.english 
                    ELSE '<from Wiktionary>' 
               END as english, thw.pos AS pos, thw.classifier as cl,
               thw.tags as tags, thw.is_compound
        FROM th_wiktionary thw
        LEFT JOIN volubilis v1 ON v1.thai = thw.word
        LEFT JOIN volubilis v2 ON v2.variants = thw.word
        WHERE thw.roman IS NOT NULL AND v1.thai IS NULL AND v2.variants IS NULL
        GROUP BY thw.word, thw.pos -- avoid multiple rows with same POSes for a given word
                
        UNION ALL
                
        SELECT thw2.word as thai, NULL, NULL, thw2.roman, 
               CASE 
                    WHEN thw2.english IS NOT NULL THEN thw2.english 
                    ELSE '<from Wiktionary>' 
               END as english, thw2.pos AS pos, thw2.classifier as cl,
               thw2.tags as tags, thw2.is_compound
        FROM th_wiktionary thw2
        WHERE thw2.missing_in_vol = 1;
    """)

    entries = defaultdict(lambda: {
        "thai": None,
        "variants": set(),
        "roman": None,
        "see_also": None,
        "glosses": []
    })

    for row in cur:
        canonical = row["thai"]
        if not canonical:
            continue

        e = entries[canonical]
        e["thai"] = canonical
        
        if row["variants"]:
            e["variants"].update(row["variants"].split(" = "))
        elif row["thai"].endswith("-"):  # prefixes from Wiktionary
            e["variants"].add(row["thai"][:-1])

        if not e["roman"]:
            e["roman"] = row["roman"]

        if row["is_compound"]:
            e["is_compound"] = True
        elif any(" " in r for r in row["roman"].split(" = ")):
            e["is_compound"] = True

        if row["see_also"]:
            e["see_also"] = row["see_also"]

        if row["english"]:
            gloss = { "en": row["english"] }

            if canonical in WIKTIONARY_PHRASES:
                if row["pos"] in {"n.", "v."}:
                    gloss["pos"] = row["pos"] + " exp."
                elif row["pos"] == "<POS missing>":
                    gloss["pos"] = "phrase"
                else:
                    gloss["pos"] = row["pos"]
            elif row["pos"] != "<POS missing>":
                gloss["pos"] = row["pos"]

            if row["tags"]:
                gloss["tags"] = row["tags"].split(", ")
            if row["cl"]:
                gloss["classifier"] = []
                for single_cl in row["cl"].split(" ; "):
                    if single_cl in CLASSIFIERS:
                        gloss["classifier"].append({
                            "thai": single_cl,
                            "roman": CLASSIFIERS[single_cl]
                        })
            e["glosses"].append(gloss)

    # Add transliterations

    cur.execute("""
        SELECT thai, translit_of, src_lang, src_script
        FROM translit
    """)

    for row in cur:
        e = entries[row["thai"]]
        
        display_text = f"{row['translit_of']}"
        is_incorrect = display_text.endswith("†")
        if is_incorrect:
            display_text = display_text[:-1]

        if row["src_script"] and row["src_lang"]:
            display_text += f" (from {row['src_lang']}: {row['src_script']})"
        elif row["src_lang"] == "Thai":
            pass
        elif row["src_lang"]:
            display_text += f" (from {row['src_lang']})"

        if is_incorrect:
            display_text += " [based on incorrect pronunciation]"
        
        e["thai"] = row["thai"]
        
        e["glosses"].append({
            "pos": "thai name" if row["src_lang"] == "Thai" else "translit. of",
            "en": display_text
        })

    # Add entities for certain categories
    ENTITY_HEADS = {
        'ตำบล',
        'ภาษา',
        'พระ',
        'โรงเรียน',
        'สโมสรฟุตบอล',
        'จังหวัด',
        'อำเภอ',
        'เทศบาลตำบล',
        'เขต',
        'พรรค',
        'แม่น้ำ',
        'มหาวิทยาลัย',
        'รัฐ',
        'เกาะ',
        'ยุทธการ',
        'ถนน',
        'วงศ์',
        'สถานี',
        'แขวง',
        'ฟาโรห์',
        'สกุล',
        'ธงชาติ',
        'แคว้น',
        'คณะกรรมการ',
        'สงคราม',
        'เทศบาลเมือง',
        'พิพิธภัณฑ์',
        'สถานีรถไฟ',
        'สะพาน',
        'โรงพยาบาล',
        'ชาว',
        'อุทยานแห่งชาติ',
        'ท่าอากาศยานนานาชาติ',
        'รถไฟใต้ดิน',
        'สนามกีฬา',
        'สหพันธ์',
        'รางวัล',
        'กองทัพ',
        'ราชวงศ์',
        'ฟุตบอลทีมชาติ',
        'ปลา',
        'อาสนวิหาร',
        'วิทยาลัย',
        'สมาคม',
        'วัน',
        'เทศ',
        'ตราแผ่นดิน',
        'ท่าอากาศยาน',
        'ปราสาท',
        'มัสยิด',
        'องค์การบริหารส่วนตำบล',
        'โรค',
        'ทะเลสาบ',
        'เขา',
        'วงศ์ปลา',
        'ประเทศ',
        'วัง',
        'สถาบัน',
        'สาธารณรัฐ',
        'สมาคมฟุตบอล',
        'สนธิสัญญา',
        'สำนักงาน',
        'หอ'
    }

    cur.execute("""
        SELECT thai, english, segmentation FROM th_wikipedia
        WHERE segmentation LIKE '[%' AND segmentation NOT LIKE '%<%'
        AND english IS NOT NULL
    """)
    for row in cur:
        head_noun = re.match(r"\[([^<>\[\]]*?)\]", row["segmentation"]).group(1)
        if head_noun in ENTITY_HEADS:
            e = entries[row["thai"]]
            e["thai"] = row["thai"]
            e["is_compound"] = "][" in row["segmentation"],
            e["glosses"].append({
                "pos": "n. prop.",
                "en": row["english"]
            })


    # Final cleanup
    output = []
    for e in entries.values():
        payload = {
            "thai": e["thai"],
            "variants": sorted(e["variants"]),
            "glosses": sorted(e["glosses"], key=lambda g: g.get("pos", None) 
                              in ["prep.", "pron.", "preposition", "pronoun"],
                              reverse=True),
        }

        if e["roman"]:
            payload["roman"] = e["roman"]
            payload["is_compound"] = " " in e["roman"].split(" = ")[0]
        if e.get("is_compound"):  # entities
            payload["is_compound"] = True

        if e["see_also"]:
            payload["see_also"] = e["see_also"]
        output.append(payload)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    print(f"✔ Exported {len(output)} entries → {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: export_json.py kaprao.db output.json")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
