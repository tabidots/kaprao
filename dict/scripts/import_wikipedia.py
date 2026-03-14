#!/usr/bin/env python3
"""
Parse Thai Wikipedia dump and populate SQLite database with cleaned titles and English translations.
Resolves redirects and extracts parallel titles from langlinks, plus English Wikipedia categories.

This version uses pre-generated TSV files for faster execution.
"""

import re
import sqlite3
import xml.etree.ElementTree as ET
from dict.scripts.paths import DB_PATH, RAW_DIR

# Wikipedia XML namespace
NS = {'mw': 'http://www.mediawiki.org/xml/export-0.11/'}

TYPOS = {
    "พิศณุโลก": "พิษณุโลก",
    "ราชวงส์": "ราชวงศ์",
    "ปฎิวัติ": "ปฏิวัติ",
    "กฏหมาย": "กฎหมาย",
    "สัมริด": "สัมฤทธิ์",
    "พันธ์ุ": "พันธุ์",
    "พรรสังคมนิยม": "พรรคสังคมนิยม",
    "นํ้า": "น้ำ"
}

exclude_cats = {"book", "painting",
                "films", # do not exclude "film actor/actresses"!
                "concert", "operas", "composition", "film series",
                "TV series", "television series",
                "video game", "song", "album", "list",  "television season", "EP",
                "disambiguation", "discography", "discographies", 
                "videography", "videographies", "comics title", "fictional people",
                "concert tour", "television special", "pay-per-view event",
                "WWE tournaments", "WWE team", "wrestling team", "wrestling championship",
                "WWE match type",
                "recurring event", "Esports teams", "professional wrestler",
                "professional wrestling", "television episode", "political catchphrase",
                "biblical phrase", "religious phrase", "political quote",
                "Hangul jamo", "alphabet stub", "specific kana", "Quranic verse",
                "Arabic letter", "Hebrew letter", "Urdu letter", "Persian letter",
                "Indic letter", "Cyrillic letter", "Greek letter",
                "Condor Trilogy", "Fiction about the imperial examination", "Fictional Changquan practitioner", 
                "Fictional characters from Beijing", "Fictional characters from Guangdong", 
                "Fictional characters from Hunan", "Fictional characters from Shaanxi", 
                "Fictional characters from Shanxi", "Fictional cult leader", "Fictional demon hunter", 
                "Fictional exorcist", "Fictional female warrior", "Fictional ghost hunter", 
                "Fictional Han dynasty people", "Fictional Mongolian people", "Fictional monster hunter", 
                "Fictional Muslim", "Fictional princesses", "Fictional Qing dynasty people", 
                "Fictional revolutionaries", "Fictional Shang dynasty people", 
                "Fictional Shaolin kung fu practitioner", "Fictional suicide", "Fictional swordfighter", 
                "Fictional tai chi practitioner", "Fictional Tang dynasty people", 
                "Fictional traditional Chinese medicine practitioner", "Fictional wushu practitioner", 
                "Fictional Yuan dynasty people", "Fictional Zui Quan practitioner", 
                "Fictional characters from Henan",
                "Investiture of the Gods character", "Jin Yong character",
                "Kamen Rider character", "Chapters in the Quran",
                "Arabic words and phrases in Sharia", "Sharia legal terminology"
                }
CATEGORIES_TO_EXCLUDE = re.compile(r"\b(?:" + r"|".join(exclude_cats) + r")s?\b", re.IGNORECASE)

one_word_cats = {"musical group"}
CATEGORIES_ONE_WORD_ONLY = re.compile(r"\b(?:" + r"|".join(one_word_cats) + r")s?\b", re.IGNORECASE)

gray_area_cats = {"anime", "manga", "manhwa", "manhua"}
# episode, season, soundtrack, character?
CATEGORIES_IN_GRAY_AREA = re.compile(r"\b(?:" + r"|".join(gray_area_cats) + r")s?\b", re.IGNORECASE)

ignore_cats = {"Wikipedia", "Article", "article", "Wikidata", "Pages containing",
               "births", "deaths", "Webarchive", "Pages using", "Pages where", "Use", "language sources",
               "Pages with", "CS1", "Year of birth", "Television",
               "no-target", "Pages overriding", "accuracy dispute"}
CATEGORIES_TO_IGNORE = re.compile(r"(?:" + r"|".join(ignore_cats) + r")")

TITLES_TO_EXCLUDE = {
    "Llanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch",
    "Llanfairpwllgwyngyll",
    "The Guo Family and Associates",
    "Taumatawhakatangihangakoauauotamateaturipukakapikimaungahoronukupokaiwhenuakitanatahu"
    "Taumatawhakatangi­hangakoauauotamatea­turipukakapikimaunga­horonukupokaiwhen­uakitanatahu",
    "Taumata­whakatangihanga­koauau­o­tamatea­turi­pukaka­piki­maunga­horo­nuku­pokai­whenua­ki­tana­tahu",
    "Taumatawhakatangi­hangakoauauotamatea­turipukakapikimaunga­horonukupokaiwhen­uakitanatahu",
    "Storm Area",  # Storm Area 51
    "Quranic studies",
    "Sansa (temple)"
    "อาอิตาอิโยะ./คิมิโตะโนะอาชิตะ",
    "ซูเปอร์เซ็นไต VS ซีรีส์เธียร์เตอร์",
    "เกคิโซเซ็นไต คาร์เรนเจอร์ VS โอเรนเจอร์",
    "เด็นจิเซ็นไต เมกะเรนเจอร์ VS คาร์เรนเจอร์",
    "เซย์จูเซ็นไต กิงกะแมน VS เมกะเรนเจอร์",
    "คิวคิวเซ็นไต โกโกไฟว์ VS กิงกะแมน",
    "มิไรเซ็นไต ไทม์เรนเจอร์ VS โกโกไฟว์",
    "นินปูเซ็นไต เฮอร์ริเคนเจอร์ VS กาโอเรนเจอร์",
    "บาคุริวเซ็นไต อาบะเรนเจอร์ VS เฮอร์ริเคนเจอร์",
    "มาโฮเซ็นไต มาจิเรนเจอร์ VS เดกะเรนเจอร์",
    "จูเคนเซ็นไต เกคิเรนเจอร์ VS โบเคนเจอร์",
    "อีชอัตเธอส์เวย์~ทะบิโนะโตะชู~",
}

# Patterns for Thai royal titles
ROYAL_TITLE_PATTERNS = [
    r'พระบาทสมเด็จพระ',           # King titles
    r'สมเด็จพระ',                  # High royal titles
    r'พระเจ้า',                    # Royal titles
    r'กรมพระ',                     # Royal department titles
    r'กรมหลวง',                    # Royal department titles
    r'กรมหมื่น',                   # Royal department titles
    r'กรมขุน',                     # Royal department titles
    r'พระองค์เจ้า',                # Prince/Princess
    r'เจ้าฟ้า',                    # Prince/Princess
    r'พระวรวงศ์เธอ',               # Royal family
    r'พระเจ้าบรมวงศ์เธอ',          # Royal family
    r'ทูลกระหม่อม',                # Princess title
    r'หม่อมเจ้า',                  # Minor royal title
    r'หม่อมราชวงศ์',               # Royal descendant
    r'เจ้าจอม'
]
ROYAL_RE = re.compile("|".join(ROYAL_TITLE_PATTERNS))

ROYAL_CATEGORIES = {
    "Ayutthaya", "Chakri", "Phra Ong Chao", "Chao Fa", "Mongkut", "Thai royalty",
    "Chula Chom Klao", "Krom Luang", "Mahidol"
}
ROYAL_CATEGORIES_RE = re.compile("|".join(ROYAL_CATEGORIES))


def has_thai(text):
    """Check if text contains at least one Thai character."""
    return bool(re.search(r'[ก-๙]', text))


def clean_title(title, clean_roman_numeral=False):
    """
    Clean title by removing dates but keeping useful parentheticals like (film).
    """
    if not title:
        return ""
    if title == "15&":
        return "15&"
    
    title = title.replace("\u200D", "")
    
    if clean_roman_numeral:
        title = re.sub(r"\b[IVXL]+\b", '', title)
        title = re.sub(r"\b[VXL]\b", '', title)

    # Normalize all hyphen-like characters to a standard hyphen
    title = re.sub(r'[–—−]', '-', title)

    # Remove other Roman numerals but not the K-pop group VIXX
    if not re.fullmatch(r"[IVXL]{2,}", title):
        title = re.sub(r"\b[IVXL]{2,}(?!-)$", "", title)

    # Military vehicle model numbers
    title = re.sub(r'\b(ซู|อิ|ที|ตู|เอ็มเอส|คิ)-\d+', r' ', title)
    title = re.sub(r'\b(Su|Ki|Tu|MS|[A-Z])-\d+', r' ', title)

    # Ordinal numbers
    title = re.sub(r" \(แก้ความกำกวม\)| \(disambiguation\)", "", title)
    title = re.sub(r"\d+(st|nd|rd|th)", " ", title)
    title = re.sub(r"(?:เที่ยวบิน|ชนิด)(?:ที่)? \d+", " ", title)
    title = re.sub(r"(?:ครั้ง)?ที่ \d+", " ", title)
    title = re.sub(r"Flight \d+", " ", title)
    title = re.sub(r" of \d+", " ", title)
    title = re.sub(
        r"(?:ครั้ง)?ที่(?:หนึ่ง|สอง|สาม|สี่|ห้า|หก|เจ็ด|แปด|เก้า|สิบ|ยี่สิบ)(?:$|\s)", " ", title)

    # Parenthetical date patterns
    title = re.sub(
        r'\(([^)]*?)(?:ค\.ศ\.|พ\.ศ\.)\s*\d+(?:[–-]\d+)?([^)]*?)\)', r'', title)
    title = re.sub(
        r'\(([^)]*?)(?:died|สิ้นพระชนม์|เกิดปี|born)\s+\d+([^)]*?)\)', r'', title)
    title = re.sub(r'\(\s*\d{4}(?:[–-]\d{2,4})?\s*\)', '', title)
    title = re.sub(r'\(ฤดูกาลที่\s*\d+(?:\s*และ\s*\d+)?\)', '', title)
    title = re.sub(r'\(seasons?\s*\d+(?:\s*and\s*\d+)?\)', '', title)
    title = re.sub(r' in season\s*\d+(?:\s*and\s*\d+)?\)', '', title)
    title = re.sub(r'\s*\([–\s]*(present|ปัจจุบัน)?\)', '', title)

    # NEW: Season year patterns (bare, not in parentheses)
    title = re.sub(r'ฤดู(?:กาล|ร้อน|หนาว)\s*\d{4}(?:[–-]\d{2,4})?', '', title)
    title = re.sub(r'season\s*\d{4}(?:[–-]\d{2,4})?', '', title)

    # NEW: Standalone year ranges (be careful not to match version numbers)
    title = re.sub(r'\b\d{4}[–-]\d{2,4}\b', '', title)  # 2015–16, 2565–66
    title = re.sub(r'\b\d{4}[–-]\d{1,2}\b', '', title)   # 2015–6 (short form)

    # Model numbers
    title = re.sub(r'\s*\([A-Z]+-\d+\)$', '', title)

    # Cleanup whitespace before continuing
    title = re.sub(r'\s+', ' ', title)

    title = re.sub(r'\(\s', '(', title)
    title = re.sub(r'\s\)', ')', title)
    title = re.sub(r'(?:พ\.ศ\.|ค\.ศ\.)\s*\d+(?:[–-]\d+)?', '', title)
    title = re.sub(r'(^|\s)\s*\[–-]\s*\d+', r'\1', title)
    title = re.sub(r'\d+\s*[–-]\s*(\s|$)', r'\1', title)
    title = re.sub(r'[–-]\s*$', '', title)
    title = re.sub(r'/[ก-ฮ](-[ก-ฮ])?$', '', title)
    title = re.sub(r' \([ก-ฮ]\)$', '', title)
    title = re.sub(r'^\s*–?\d+\s+|\s+\d+\s+|\s+\d+–?\s*$', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'\s*–\s* ', ' ', title)
    title = re.sub(r'^.+#', '', title)

    for subst, repl in TYPOS.items():
        title = re.sub(subst, repl, title)

    # Some weird titles with isolated Thai characters at the end
    title = re.sub(r' เ ร า\s*$', '', title)
    title = re.sub(r'[\s\d][ก-ฮ]\.?\s*$', '', title)
    title = title.replace(" (ข.ก.๕)", "")

    # Normalize nikkahit + sara aa to sara am
    title = title.replace('ํา', "ำ")
        
    title = re.sub(r'[\u200B\u200C]', '', title)

    return title.strip()


def load_redirects(redirect_path):
    """Load Thai redirects from redirect.sql.gz file."""
    print(f"Loading Thai redirects from {redirect_path}...")

    insert_pattern = re.compile(r"INSERT INTO `redirect` VALUES \((.+)\);")
    redirects = {}

    with open(redirect_path, 'rt', encoding='utf-8', errors='replace') as f:
        for line in f:
            match = insert_pattern.search(line)
            if not match:
                continue

            values_str = match.group(1)
            rows = values_str.split('),(')

            for row in rows:
                # redirect structure: (rd_from/page_id, rd_namespace, rd_title, ...)
                m = re.search(r'^(\d+),(\d+),\'(.+?)\',', row)
                if not m:
                    continue

                page_id = m.group(1)
                namespace = m.group(2)

                # Only process namespace 0 (main articles)
                if namespace != '0':
                    continue

                target_title = m.group(3)
                if target_title[0] + target_title[-1] == '""':
                    target_title = target_title[1:-1]
                # Unescape and normalize
                target_title = target_title.replace('\\\\', '\\').replace(
                    '\\"', '"').replace("\\'", "'").replace('_', ' ')
                if "#" in target_title:
                    target_title = target_title.split("#")[0]

                redirects[page_id] = target_title

    print(f"Loaded {len(redirects)} Thai redirects")
    return redirects


def load_page_ids(page_path):
    """Load Thai page IDs from page.sql file."""
    print(f"Loading Thai page IDs from {page_path}...")

    insert_pattern = re.compile(r"INSERT INTO `page` VALUES \((.+)\);")
    page_ids = {}

    with open(page_path, 'rt', encoding='utf-8', errors='replace') as f:
        for line in f:
            match = insert_pattern.search(line)
            if not match:
                continue

            values_str = match.group(1)
            rows = values_str.split('),(')

            for row in rows:
                # page structure: (page_id, namespace, title, is_redirect, ...)
                m = re.search(r'^(\d+),(\d+),\'(.+?)\',[01]', row)
                if not m:
                    continue

                page_id = m.group(1)
                namespace = m.group(2)

                # Only process namespace 0 (main articles)
                if namespace != '0':
                    continue

                title = m.group(3)
                if title[0] + title[-1] == '""':
                    title = title[1:-1]
                # Unescape and normalize
                title = title.replace('\\\\', '\\').replace(
                    '\\"', '"').replace("\\'", "'").replace('_', ' ')

                page_ids[page_id] = title

    print(f"Loaded {len(page_ids)} Thai page IDs")
    return page_ids


def resolve_redirects(redirects, page_ids):
    """Resolve redirect chains to final targets using page_id->title and page_id->target mappings."""
    print(f"Resolving redirect chains...")

    # Build title -> page_id map for lookup
    title_to_page_id = {title: page_id for page_id, title in page_ids.items()}

    resolved = {}

    for src_page_id, target_title in redirects.items():
        visited = {src_page_id}
        current_title = target_title

        # Follow redirect chain
        while current_title in title_to_page_id:
            next_page_id = title_to_page_id[current_title]

            # Check if this page is also a redirect
            if next_page_id not in redirects:
                break

            # Prevent infinite loops
            if next_page_id in visited:
                break
            visited.add(next_page_id)

            current_title = redirects[next_page_id]

        # Store as source_page_id -> final_title
        if src_page_id in page_ids:
            src_title = page_ids[src_page_id]
            resolved[src_title] = current_title

    print(f"Resolved {len(resolved)} redirect chains")
    return resolved


def load_en_page_ids(tsv_path):
    """Load English page IDs from TSV file."""
    print(f"Loading English page IDs from {tsv_path}...")

    en_page_ids = {}
    with open(tsv_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) == 2:
                title, page_id = parts
                en_page_ids[title] = int(page_id)

    print(f"Loaded {len(en_page_ids)} English page IDs")
    return en_page_ids


def load_en_categorylinks(tsv_path):
    """Load English category links from TSV file."""
    print(f"Loading English category links from {tsv_path}...")

    page_to_cat_ids = {}
    all_cat_ids = set()

    with open(tsv_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) == 2:
                page_id, cat_ids_str = parts
                cat_ids = [int(cid) for cid in cat_ids_str.split(',')]
                page_to_cat_ids[int(page_id)] = cat_ids
                all_cat_ids.update(cat_ids)

    print(f"Loaded category links for {len(page_to_cat_ids)} pages")
    print(f"Found {len(all_cat_ids)} unique category IDs")
    return page_to_cat_ids


def load_en_categories(tsv_path):
    """Load English category names from TSV file."""
    print(f"Loading English category names from {tsv_path}...")

    cat_id_to_name = {}
    with open(tsv_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) == 2:
                cat_id, cat_name = parts
                cat_id_to_name[int(cat_id)] = cat_name

    print(f"Loaded {len(cat_id_to_name)} category names")
    return cat_id_to_name


def load_langlinks(langlinks_path, redirects, page_ids):
    """Load Thai page ID -> English title mappings from TSV file."""
    print(f"Loading langlinks from {langlinks_path}...")

    # Build title->page_id map for redirect resolution
    title_to_page_id = {title: page_id for page_id, title in page_ids.items()}

    langlinks = {}
    with open(langlinks_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) == 2:
                page_id, en_title = parts

                # Resolve Thai page_id if it's a redirect
                if page_id in redirects:
                    target_title = redirects[page_id]
                    # Get the target's page_id
                    if target_title in title_to_page_id:
                        page_id = title_to_page_id[target_title]

                langlinks[page_id] = en_title

    print(f"Loaded {len(langlinks)} langlinks")
    return langlinks


def create_table(db_path, titles_with_english, redirects, en_page_ids, en_categories):
    """Create SQLite database with cleaned, deduplicated titles and English categories."""
    print(f"\nCreating table in {db_path}...")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Drop and recreate table
        cursor.execute("DROP TABLE IF EXISTS th_wikipedia")
        cursor.execute("""
            CREATE TABLE th_wikipedia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thai TEXT UNIQUE NOT NULL,
                english TEXT,
                categories TEXT,
                has_oov BOOLEAN DEFAULT 1,
                head_noun TEXT,
                segmentation TEXT,
                longest_oov TEXT,
                is_royal BOOLEAN DEFAULT 0
            )
        """)

        # Track which titles to keep
        final_titles = {}

        for thai_title, en_title in titles_with_english.items():
            # Skip if it's a redirect source
            if thai_title in redirects:
                continue
            # Or if it's a list - check the Thai in case there's no parallel article
            if thai_title.startswith("รายชื่อ"):
                continue
            if thai_title in TITLES_TO_EXCLUDE:
                continue
            if ": " in thai_title or " VS " in thai_title:
                continue

            is_royal = False
            could_have_roman_numeral = re.search(r"\d+", thai_title) or re.search(
                r"ที่(?:หนึ่ง|สอง|สาม|สี่|ห้า|หก|เจ็ด|แปด|เก้า|สิบ|ยี่สิบ)", thai_title)

            # Clean the title
            cleaned = clean_title(thai_title)
            if ROYAL_RE.search(thai_title):
                is_royal = True

            # Clean the English title only when using it
            cleaned_en = clean_title(en_title, clean_roman_numeral=could_have_roman_numeral) if en_title else None

            # Must have Thai characters
            if not has_thai(cleaned):
                continue

            # Skip empty/invalid titles
            if not cleaned: 
                continue
            if len(cleaned) == 1:
                continue
            if not cleaned_en:
                pass
            elif cleaned_en.startswith("WWE "):
                continue
            elif cleaned_en.startswith("Taumata"):
                continue
            elif cleaned_en in TITLES_TO_EXCLUDE:
                continue

            if cleaned not in final_titles:
                # Get English categories if we have an English title
                cats_str = None
                base_en_title = None
                if en_title:
                    if "#" in en_title:
                        base_en_title = en_title.split('#')[0]
                    else:
                        base_en_title = en_title
                if base_en_title and base_en_title in en_page_ids:
                    en_page_id = en_page_ids[base_en_title]
                    cats = en_categories.get(en_page_id, [])
                    word_count = len(base_en_title.split(' '))

                    cats = [cat for cat in cats if not CATEGORIES_TO_IGNORE.search(cat)]
                    if word_count > 6:
                        continue
                    if any(CATEGORIES_TO_EXCLUDE.search(cat) for cat in cats):
                        continue
                    if any(CATEGORIES_ONE_WORD_ONLY.search(cat) for cat in cats) and word_count > 1:
                        continue
                    if any(CATEGORIES_IN_GRAY_AREA.search(cat) for cat in cats) and not any(re.search(r"writer|creator", cat) for cat in cats):
                        continue
                    if any(ROYAL_CATEGORIES_RE.search(cat) for cat in cats):
                        is_royal = True
                    if cats:
                        cats_str = '; '.join(cats)

                final_titles[cleaned] = (cleaned_en, cats_str, is_royal)

        # Insert into database
        data = [(thai, eng, cats, is_royal)
                for thai, (eng, cats, is_royal) in final_titles.items()]
        
        cursor.executemany(
            "INSERT INTO th_wikipedia (thai, english, categories, is_royal) VALUES (?, ?, ?, ?)", data)

        conn.commit()

        print(f"Inserted {len(data)} unique Thai titles")
        print(f"  - {sum(1 for _, e, _, _ in data if e)} with English translations")
        print(
            f"  - {sum(1 for _, e, _, _ in data if not e)} without English translations")
        print(f"  - {sum(1 for _, _, c, _ in data if c)} with categories")

        cursor.execute("""
            DELETE FROM th_wikipedia 
            WHERE rowid IN (
                SELECT thw.rowid 
                FROM th_wikipedia thw
                JOIN volubilis v ON thw.thai = v.thai
            );
        """)

        conn.commit()

        print(f"Deleted {cursor.rowcount} Thai titles already in Volubilis dataset")


def main():
    # Thai Wikipedia SQL files
    TH_REDIRECT_PATH = RAW_DIR / "thwiki-20260101-redirect.sql"
    TH_PAGE_PATH = RAW_DIR / "thwiki-20260101-page.sql"

    # TSV files (pre-generated)
    LANGLINKS_PATH = RAW_DIR / "thwiki-20260101-langlinks.tsv"
    EN_PAGE_IDS_TSV = RAW_DIR / "enwiki-20260101-pageids.tsv"
    EN_CATEGORYLINKS_TSV = RAW_DIR / "enwiki-20260101-categorylinks.tsv"
    EN_CATEGORIES_TSV = RAW_DIR / "enwiki-20260101-linktarget.tsv"

    # Step 1: Load Thai redirects from SQL file
    redirects_raw = load_redirects(TH_REDIRECT_PATH)

    # Step 2: Load Thai page IDs from SQL file
    page_ids = load_page_ids(TH_PAGE_PATH)

    # Step 3: Resolve redirect chains
    redirects = resolve_redirects(redirects_raw, page_ids)

    # Step 4: Load langlinks (Thai -> English title mapping) - pass redirects for resolution
    langlinks = load_langlinks(LANGLINKS_PATH, redirects_raw, page_ids)

    # Step 5: Build title -> English mapping
    titles_with_english = {}
    for page_id, title in page_ids.items():
        en_title = langlinks.get(page_id, None)
        titles_with_english[title] = en_title

    # Step 5: Load pre-generated English data from TSV files
    en_page_ids = load_en_page_ids(EN_PAGE_IDS_TSV)
    page_to_cat_ids = load_en_categorylinks(EN_CATEGORYLINKS_TSV)
    cat_id_to_name = load_en_categories(EN_CATEGORIES_TSV)

    # Step 6: Build final page_id -> [category_names] mapping
    print(f"\nResolving category IDs to names...")
    en_categories = {}
    for page_id, cat_ids in page_to_cat_ids.items():
        category_names = []
        for cat_id in cat_ids:
            if cat_id in cat_id_to_name:
                category_names.append(cat_id_to_name[cat_id])
        if category_names:
            en_categories[page_id] = category_names

    print(f"Resolved categories for {len(en_categories)} pages")

    # Step 7: Create database
    create_table(DB_PATH, titles_with_english,
                 redirects, en_page_ids, en_categories)

    print("\nDone!")


if __name__ == "__main__":
    main()