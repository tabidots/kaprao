from dict.scripts.paths import DB_PATH, RAW_DIR
from dict.scripts.phonetic_utils import paiboon_to_aua, make_tltk, romanize_from_tltk
import json
import sqlite3
import re

# The only allowed variant pronunciations are compounds (also tagged as "bound form")
# and they will be distinguished by adding a hyphen to the end
# The remaining variants are excluded, including informal/colloquial pronunciations
# (of which there are only 12, so not important)

PRONUNCIATION_TAGS_TO_EXCLUDE = {'slang', 'dated', 'rare', 'internet', 'now rare',
                   'พบในร้อยกรอง', 'sometimes considered nonstandard', 'law',
                   'informal', 'colloquial'}

GLOSS_TAGS_TO_EXCLUDE = {'rare', 'obsolete', 'archaic', 'dated'}

ALLOWED_POS = {
    "adj": "adjective",
    "adj_noun": "noun",
    "adv": "adverb",
    "affix": "affix",
    "classifier": "classifier",
    "conj": "conjunction",
    "contraction": "contraction",
    "det": "determiner",
    "intj": "interjection",
    "name": "proper noun",
    "noun": "noun",
    "num": "numeral",
    "particle": "particle",
    "phrase": "phrase",
    "prefix": "prefix",
    "prep": "preposition",
    "prep_phrase": "prepositional phrase",
    "pron": "pronoun",
    "proverb": "proverb",
    "suffix": "suffix",
    "symbol": "noun",  # weird thing with the word "gold"
    "verb": "verb"
}

GLOSS_TAGS = {
    # Register and formality
    "ภาษาปาก": "colloquial",
    "คำสุภาพ": "polite",
    "ทางการ": "formal",
    "ไม่ทางการ": "informal",
    "ราชาศัพท์": "royal",
    "ภาษาหนังสือ": "literary",

    # Frequency and usage
    "ล้าสมัย": "dated",
    "โบราณ": "archaic",
    "พบได้ยาก": "rare",
    "ปัจจุบันไม่ค่อยใช้": "rare",
    "เลิกใช้": "obsolete",
    "ภาษาปัจจุบัน": "current",

    # Slang and style
    "แสลง": "slang",
    "youth สแลง": "slang",
    "fandom slang": "slang",
    "สแลงอินเตอร์เน็ต": "internet slang",
    "สำนวน": "idiomatic",
    "ภาษาพูด": "spoken",
    "ภาษาเขียน": "written",

    # Geographic
    "ภาษาถิ่น": "dialectal",
    "ถิ่น": "dialectal",
    "อีสาน": "Isan",
    "เหนือ": "Northern",
    "ใต้": "Southern",
    "กรุงเทพฯ": "Bangkok",

    # Technical domains
    "กฎหมาย": "law",
    "การทหาร": "military",
    "วิทยาศาสตร์": "science",
    "คณิตศาสตร์": "mathematics",
    "แพทยศาสตร์": "medicine",
    "ดนตรี": "music",
    "คอมพิวเตอร์": "computing",
    "ภูมิศาสตร์": "geography",
    "เคมี": "chemistry",
    "ฟิสิกส์": "physics",
    "ชีววิทยา": "biology",
    "ภาษาศาสตร์": "linguistics",
    "ไวยากรณ์": "grammar",

    # Religion
    "ศาสนาพุทธ": "Buddhism",
    "ศาสนาฮินดู": "Hinduism",
    "ศาสนาอิสลาม": "Islam",
    "ศาสนาคริสต์": "Christianity",
    "พระพุทธศาสนา": "Buddhism",

    # Tone and connotation
    "ดูหมิ่น": "derogatory",
    "หยาบคาย": "vulgar",
    "ไม่สุภาพ": "impolite",
    "เหยียดหยาม": "pejorative",
    "เหยียดเพศ": "sexist",
    "ประชด": "ironic",
    "อภิธานศัพท์": "jargon",

    # Other
    "ตัวย่อ": "abbreviation",
    "อักษรย่อ": "initialism",
    "สะกดผิด": "misspelling",
    "สะกดแบบอื่น": "alternative spelling",
    "คำย่อ": "abbreviation",
    "คำเปรียบเทียบ": "figurative",
    "โดยเปรียบเทียบ": "figuratively",
    "ภาษาปาก": "colloquial",
    "ภาษาไม่มาตรฐาน": "nonstandard",
    "ควรระวัง": "careful usage",
    "ไม่ควรใช้": "proscribed",
    "บันเทิงคดี": "fiction",
    "ประวัติศาสตร์": "history",
    "ตำนาน": "mythology",
}

CLASSIFIER_RE = re.compile(
    r"\s*\(Classifi?ers?\:? (.+)\)\s*(?=[\w\d;]|$)", re.IGNORECASE)

unromanized_thai = set()

def annotate_thai(text, roman_lookup=None):
    """
    Annotate Thai text with romanizations where available.
    roman_lookup: dict mapping Thai -> roman (from Volubilis)
    """
    if not text:
        return text

    # PASS 1: Handle already parenthesized Paiboon romanizations
    # Pattern: Thai (paiboon) or Thai (paiboon, "gloss")
    paiboon_pattern = re.compile(
        r'\[?\b([ก-๙]+(?: [ก-๙]+)+|[ก-๙][ก-๙\.]*)\s*\(([^ก-๙]+?)(?:,?\s*["“]([^"”]+)["”])?\)'
    )

    def replace_paiboon(m):
        if m.group(0).startswith("["):
            return m.group(0)
        thai, paiboon, gloss = m.groups()
        aua = paiboon_to_aua(paiboon)
        if gloss:
            return f"[{thai} ({aua}, “{gloss}”)]"
        return f"[{thai} ({aua})]"

    text = paiboon_pattern.sub(replace_paiboon, text)

    # PASS 2: Handle bare Thai in parentheses (no romanization yet)
    # Pattern: (Thai) but not (Thai numeral: ๕)
    bare_thai_pattern = re.compile(
        r'\(([ก-๙]+(?: [ก-๙]+)+|[ก-๙][ก-๙\.]*)\)'
    )

    def replace_bare_thai(m):
        thai = m.group(1)
        if roman_lookup and thai in roman_lookup:
            return f"[{thai} ({roman_lookup[thai]})]"
        else:
            unromanized_thai.add(thai)
            return m.group(0)  # Keep original

    text = bare_thai_pattern.sub(replace_bare_thai, text)


    # PASS 3: Handle Thai without parentheses (standalone)
    standalone_pattern = re.compile(
        r'\[?\b([ก-๙]+(?: [ก-๙]+)+|[ก-๙][ก-๙\.]*)(?![ก-๙\)\]\d])'
    )

    def replace_standalone(m):
        if m.group(0).startswith("["):
            return m.group(0)
        thai = m.group(1)

        # Skip if it's a numeral or looks like part of a larger pattern
        if re.match(r'^[๐-๙]+$', thai):  # Thai numerals
            return m.group(0)

        if roman_lookup and thai in roman_lookup:
            return f"[{thai} ({roman_lookup[thai]})]"
        else:
            unromanized_thai.add(thai)
            return m.group(0)

    text = standalone_pattern.sub(replace_standalone, text)

    return text

SKIP_LIST = {
    'คัลมืยเคีย', 'ชายสามโบสถ์', 'ฝ่าคมหอกคมดาบ', 'แก้มช้ำ', 'สวดโอ้เอ้วิหารราย', 'ผ้าขนสัตว์', 
    'ภูมิลำเนาของนิติบุคคล', 'แง๊ะ', 'ความสุกขี', "ᩈᩮᩬᩥ᩶ᩋ"
}


def parse_wiktionary(filepath, conn, seen_words, src="enwiki"):
    c = conn.cursor()
    batch = []

    with open(filepath, "r") as f:
        for line in f:
            # Parse each line as JSON
            try:
                data = json.loads(line)

                word = data['word']
                if src == "thwiki" and word in seen_words:
                    continue
                if len(word) == 1:
                    continue
                if word in SKIP_LIST:
                    continue

                # Ignore words with no pronunciation data at all
                # (But Thai Wiktionary entries with only phonemic respellings are OK)
                sounds = data.get("sounds")
                if not sounds:
                    continue

                # Is the word a compound?
                etym = ""
                if data.get("etymology_texts"):
                    etym = data['etymology_texts'][0]
                elif data.get("etymology_text"):
                    etym = data['etymology_text']
                
                is_compound = False
                if re.match(r"(From )?[ก-๙]+(?: \([^+ก-๙]+\))? \+ [ก-๙]+(?: \([^+ก-๙]+\))?", etym):
                    is_compound = True
                elif word in ("กรุงรัตนโกสินทร์", "กรุงศรีอยุธยา", "กรุงสุโขทัย"):
                    is_compound = True

                pos = None
                if wiki_pos := data.get("pos", None):
                    pos = ALLOWED_POS.get(wiki_pos, None)
                    # Reject words with anomalous POS
                    # "character" w/length > 1 (ฤๅ, ฦๅ) and "punct" (ฯลฯ)
                    if not pos:
                        print(f"Skipping word: {word}, unknown pos: {wiki_pos}")
                        continue

                # Pronunciation
                if any(s.get("raw_tags") for s in sounds):
                    for s in sounds:
                        if not s.get("raw_tags"):
                            continue
                        if not s.get("tags"):
                            s['tags'] = []
                        s['tags'].extend(s['raw_tags'])

                respellings = [s for s in sounds if "phoneme" in s.get("tags", []) or "Phonemic" in s.get("tags", [])]
                paiboons = [s for s in sounds if "Paiboon" in s.get("tags", [])]
                try:
                    for i, respelling in enumerate(respellings):
                        paiboons[i]['tags'].extend(respelling['tags'])
                except IndexError:
                    print(f"Failed to parse word: {word}")
                    continue

                paiboon_rom_list, roman_list = [], []
                prefix_paiboon_list, prefix_roman_list = [], []
                
                if not paiboons and src == "thwiki":
                    # For Thai Wiktionary entries with only phonemic respellings
                    tltk = make_tltk(word)
                    roman = romanize_from_tltk(tltk)
                    if not roman:
                        print(f"Failed to parse word: {word}")
                        continue
                    if pos == "prefix":
                        roman += "-"
                    roman_list.append(roman)

                for paiboon in paiboons:
                    tags = {t.lower() for t in paiboon['tags']}
                    pb = paiboon['roman']
                    if pb in paiboon_rom_list:
                        continue
                    if tags & PRONUNCIATION_TAGS_TO_EXCLUDE:
                        continue
                    if pos == "prefix":
                        pb += "-"
                    if tags & {'compound', 'bound form'}:
                        prefix_paiboon_list.append(pb)
                        prefix_roman_list.append(paiboon_to_aua(pb))
                    else:
                        paiboon_rom_list.append(pb)
                        roman_list.append(paiboon_to_aua(pb))
            
                paiboon = ' = '.join(paiboon_rom_list) if paiboon_rom_list else None
                roman = ' = '.join(roman_list) if roman_list else None
                prefix_paiboon = ' = '.join(prefix_paiboon_list) if prefix_paiboon_list else None
                prefix_roman = ' = '.join(prefix_roman_list) if prefix_roman_list else None

                if word == "เวทนา":
                    paiboon = "wee-tá-naa" if pos == "noun" else "wêet-tá-naa"
                    roman = "wee•thá•naa" if pos == "noun" else "wêet•thá•naa"

                senses = data.get("senses", None)
                if not senses:
                    print(f"Skipping word: {word}, no senses")
                    continue

                for sense in senses:
                    glosses = sense.get("glosses", [])
                    
                    # Tags
                    raw_tags = sense['qualifier'].split(", ") if sense.get(
                        "qualifier") else sense.get("raw_tags", [])
                    raw_tags += sense.get("tags", [])
                    tags = []
                    qualifiers = []
                    for tag in raw_tags:
                        if tag in GLOSS_TAGS:
                            tags.append(GLOSS_TAGS[tag])
                        elif tag in GLOSS_TAGS.values():
                            tags.append(tag)
                        else:
                            qualifiers.append(tag)
                    if any(tag in GLOSS_TAGS_TO_EXCLUDE for tag in tags):
                        continue
                    tags.sort()
                    tags = ', '.join(tags) if tags else None

                    # Meanings
                    eng_def, thai_def = None, None
                    definitions = []
                    for x in glosses:
                        d = re.sub(r"\s*⇒.+$", "", x).strip(".:")
                        if d:
                            definitions.append(d)

                    if src == "thwiki":
                        thai_def = '; '.join(definitions)
                        if qualifiers:
                            f"[{', '.join(qualifiers)}] {thai_def}"

                        classifiers = [x["classifier"] for x in sense.get("classifiers", [])]
                        
                    else:
                        eng_def = '; '.join(definitions).strip(".")
                        if qualifiers:
                            f"[{', '.join(qualifiers)}] {eng_def}"
                        # Exclude any definition that is actually for a collocation
                        if re.match(r"\([ก-๙ ,~]+?~\)", eng_def):
                            continue
                        
                        classifiers = []
                        for m in re.finditer(CLASSIFIER_RE, eng_def):
                            classifiers.extend(re.findall(r"[ก-๙]{2,}", m.group(1)))
                        eng_def = re.sub(CLASSIFIER_RE, "", eng_def)
                        eng_def = annotate_thai(eng_def)
                        
                    classifier = " ; ".join(
                        [c for c in classifiers if c]) if classifiers else None

                    if roman:
                        batch.append((word, paiboon, roman, pos, eng_def, thai_def, classifier, tags, is_compound))
                    if prefix_roman:
                        if word + "-" in seen_words:
                            break
                        if roman:
                            eng_def = "<same as non-prefix meaning>"
                            seen_words.add(word + "-")
                        batch.append((word + "-", prefix_paiboon, prefix_roman,
                                     "prefix", eng_def, thai_def, classifier, tags, is_compound))

                    # Add collocations
                    if src == "enwiki" and (exs := sense.get("examples")):
                        for e in exs:
                            if not e.get("type", None) or e["type"] != 'example':
                                continue
                            e_paiboon = e.get("roman", None)
                            e_english = e.get("english", None)
                            if not e_paiboon or not e_english:
                                continue
                            
                            e_paiboon = e_paiboon.replace(" · ", " ").replace("- ", "-")
                            if (e_translation := e.get("translation", None)) and e_translation != e_english:
                                e_english = f"{e_translation} (lit.: {e_english})"
                            
                            # Exclude complete sentences
                            if re.match(r"(\(literally\) )?\[?[A-Z]", e_english):
                                continue
                            if any(e_english.endswith(punct) for punct in ".!?"):
                                continue
                            if e_english.startswith("..."):
                                continue

                            if m := re.search(r"(.+)\s*\(literally\)\s*(.+)$", e_english):
                                main = m.group(1)
                                literal = m.group(2)
                                e_english = f"{main} (lit.: {literal})"
                            
                            e_roman = paiboon_to_aua(e_paiboon)
                            batch.append((e["text"], e_paiboon, e_roman, "phrase", e_english, None, None, None, True))

                if src == "enwiki":
                    seen_words.add(word)

                if len(batch) >= 1000:
                    c.executemany("""
                        INSERT INTO th_wiktionary 
                                  (word, paiboon, roman, pos, english, thai_def, classifier, tags, is_compound) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, batch)
                    conn.commit()
                    batch = []
                
            except json.JSONDecodeError as e:
                print(f"Error parsing line: {line}")
                print(e)
            
        if batch:
            c.executemany("""
                INSERT INTO th_wiktionary 
                            (word, paiboon, roman, pos, english, thai_def, classifier, tags, is_compound) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()

        print(f"Done!")


def main():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS th_wiktionary")
        c.execute("""CREATE TABLE IF NOT EXISTS th_wiktionary (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        word TEXT NOT NULL,
                        paiboon TEXT,
                        roman TEXT,
                        pos TEXT,
                        english TEXT,
                        thai_def TEXT,
                        classifier TEXT,
                        tags TEXT,
                        is_compound BOOLEAN
                    )
            """)

        seen_words = set()

        # Prioritize pronunciations from English Wiktionary over Thai Wiktionary

        ENWIKI_PATH = RAW_DIR / "kaikki.org-dictionary-Thai.jsonl"
        parse_wiktionary(ENWIKI_PATH, conn, seen_words, src="enwiki")

        THWIKI_PATH = RAW_DIR / "kaikki-thwiktionary-filtered.jsonl"
        parse_wiktionary(THWIKI_PATH, conn, seen_words, src="thwiki")

        print("Adding AUA romanizations for completion of English definitions...")
        c.execute("""
            CREATE TEMP TABLE unromanized (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thai TEXT NOT NULL,
                roman TEXT
            )
        """)
        c.executemany("""
            INSERT INTO unromanized (thai) VALUES (?)
        """, [(w,) for w in unromanized_thai])

        c.execute("""
            UPDATE unromanized 
            SET roman = v.roman
            FROM volubilis v
            WHERE unromanized.thai = v.thai 
                AND unromanized.roman IS NULL
        """)

        c.execute("""
            SELECT id, thai FROM unromanized WHERE roman IS NULL
        """)
        batch = []
        for (id, thai) in c.fetchall():
            tltk = make_tltk(thai)
            if not tltk:
                continue
            roman = romanize_from_tltk(tltk)
            batch.append((roman, id))

        c.executemany("""
            UPDATE unromanized
            SET roman = ?
            WHERE id = ?
        """, batch)
        conn.commit()

        c.execute("""
            SELECT thai, roman FROM unromanized WHERE roman IS NOT NULL
        """)
        roman_lookup_dict = {t: r for t, r in c.fetchall()}

        c.execute("""
            SELECT id, english FROM th_wiktionary
            WHERE thai_def IS NULL AND english GLOB '*[ก-๙]*'
        """)
        batch = []
        for (id, english) in c.fetchall():
            new_english = annotate_thai(english, roman_lookup_dict)
            if new_english != english:
                batch.append((new_english, id))

        c.executemany("""
            UPDATE th_wiktionary
            SET english = ?
            WHERE id = ?
        """, batch)
        conn.commit()

        print("Done!")


def add_abbreviations():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, thai_def FROM th_wiktionary WHERE thai_def LIKE 'อักษรย่อของ %';
        """)
        results = c.fetchall()
        batch = []
        for (id, thai_def) in results:
            full_form = thai_def[len("อักษรย่อของ "):]
            c.execute("""
                SELECT thai, roman, GROUP_CONCAT(english, '; ') FROM volubilis WHERE thai = ?
                GROUP BY thai, roman
            """, (full_form,))
            v_results = c.fetchall()
            expansions = []
            for (thai, roman, english) in v_results:
                expansions.append(f'[{thai} ({roman})] {english}')
            if expansions:
                eng_def = "abbreviation of " + " or ".join(expansions)
                batch.append((eng_def, id))

        c.executemany("""
            UPDATE th_wiktionary
            SET english = ?
            WHERE id = ?
        """, batch)
        conn.commit()
                


def flag_missing_pos_entries():
    """
    Flag Wiktionary entries where the POS exists in Wiktionary but not in Volubilis.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        # Add column if it doesn't exist
        try:
            cur.execute(
                "ALTER TABLE th_wiktionary ADD COLUMN missing_in_vol INTEGER DEFAULT 0")
        except:
            # Column already exists, just reset it
            cur.execute("UPDATE th_wiktionary SET missing_in_vol = 0")

        # Create temp table with words and their POS coverage in Volubilis
        cur.execute("""
            CREATE TEMP TABLE IF NOT EXISTS vol_pos_coverage AS
            SELECT 
                thai,
                MAX(CASE WHEN pos LIKE 'v%' THEN 1 ELSE 0 END) as has_verb,
                MAX(CASE WHEN pos LIKE 'n%' OR pos = 'org.' THEN 1 ELSE 0 END) as has_noun
            FROM volubilis
            GROUP BY thai;
        """)

        # Create index for fast lookup
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_vol_coverage ON vol_pos_coverage(thai);")

        # Flag Wiktionary entries that supplement Volubilis
        cur.execute("""
            UPDATE th_wiktionary
            SET missing_in_vol = 1
            WHERE pos IN ('verb', 'noun')
            AND word IN (SELECT thai FROM vol_pos_coverage)
            AND (
                (pos = 'noun' AND word IN (
                    SELECT thai FROM vol_pos_coverage WHERE has_noun = 0
                ))
                OR
                (pos = 'verb' AND word IN (
                    SELECT thai FROM vol_pos_coverage WHERE has_verb = 0
                ))
            );
        """)

        rows_updated = cur.rowcount
        print(f"Flagged {rows_updated} Wiktionary entries to supplement Volubilis")

        # Clean up
        cur.execute("DROP TABLE IF EXISTS vol_pos_coverage;")

        conn.commit()

        return rows_updated


if __name__ == "__main__":
    main()
    add_abbreviations()
    flag_missing_pos_entries()