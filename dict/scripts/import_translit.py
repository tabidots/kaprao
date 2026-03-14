from dict.scripts.paths import DB_PATH, RAW_DIR
from dict.scripts.lexicon import LATIN_LETTER_NAMES
import sqlite3
import csv
import re

LATIN_LETTER_MAP = {
    "A": ["เอ"],
    "B": ["บี"], 
    "C": ["ซี"],
    "D": ["ดี"],
    "E": ["อี"],
    "F": ["เอฟ"],
    "G": ["จี"],
    "H": ["เอช"],
    "I": ["ไอ"],
    "J": ["เจ"],
    "K": ["เค"],
    "L": ["แอล"],  # เอ็ล - German
    "M": ["เอ็ม"],
    "N": ["เอ็น"],
    "O": ["โอ"],
    "P": ["พี"],
    "Q": ["คิว"],
    "R": ["อาร์"],
    "S": ["เอส"],  # เอ็ส - German
    "T": ["ที"],
    "U": ["ยู"],
    "V": ["วี"],  # เฟา - German, Polish; อูเบ - Spanish
    "W": ["ดับเบิลยู", "ดับเบิ้ลยู"],  # Two different ways to write W
    # ดับบลิว - alternate in English
    "X": ["เอ็กซ์"], 
    # เอกซ์ - alternate in English
    "Y": ["วาย"], 
    "Z": ["ซี", "แซด", "เซด"]  # Three different ways to write Z
    # เซ็ท - German, เซ็ด - Dutch
}


def is_latin(char):
    """
    Check if a single character is within the Latin Unicode blocks.
    """
    code = ord(char)
    # Latin blocks
    return (
        # Basic Latin (ASCII)
        0x0000 <= code <= 0x007F or
        # Latin-1 Supplement (includes accented characters)
        0x0080 <= code <= 0x00FF or
        # Latin Extended-A
        0x0100 <= code <= 0x017F or
        # Latin Extended-B
        0x0180 <= code <= 0x024F or
        # IPA Extensions
        0x0250 <= code <= 0x02AF or
        # Latin Extended Additional
        0x1E00 <= code <= 0x1EFF or
        # Latin Extended-C
        0x2C60 <= code <= 0x2C7F or
        # Latin Extended-D
        0xA720 <= code <= 0xA7FF or
        # Latin Extended-E
        0xAB30 <= code <= 0xAB6F
    )


def has_non_latin(text):
    """
    Returns True if any character in the string is not Latin.
    """
    return any(not is_latin(char) for char in text)



def main():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS translit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thai TEXT,
                src_script TEXT,
                src_lang TEXT,
                translit_of TEXT
            )  
        """)

        batch = []
        with open(RAW_DIR / "transliterations.tsv", "r") as f:
            reader = csv.DictReader(f, delimiter="\t")
            next(reader)
            for row in reader:
                thai = row["thai"]
                src_lang = None
                src_script = None
                if m := re.match(r"^(.+?)\s+\((.+?)(?:(?: - )(.+))?\)(†)?$", row["translit_of"]):
                    if has_non_latin(m.group(1)):
                        src_script = m.group(1)
                        translit_of = m.group(2)
                    if m.group(3):
                        src_lang = m.group(3)
                    if m.group(4):
                        translit_of += "†"
                else:
                    translit_of = row["translit_of"]
                
                batch.append((thai, src_script, src_lang, translit_of))

                if len(batch) >= 1000:
                    c.executemany("""
                        INSERT OR REPLACE INTO translit (thai, src_script, src_lang, translit_of)
                        VALUES (?, ?, ?, ?)
                    """, batch)
                    batch = []

        if batch:
            c.executemany("""
                INSERT OR REPLACE INTO translit (thai, src_script, src_lang, translit_of)
                VALUES (?, ?, ?, ?)
            """, batch)


NATIONALITIES = {
    "Afghan", "Albanian", "Algerian", "American", "Andorran", "Angolan", "Anguillan", "Citizen of Antigua and Barbuda", "Argentine", "Armenian", "Australian", "Austrian", "Azerbaijani", "Bahamian", "Bahraini", "Bangladeshi", "Barbadian", "Belarusian", "Belgian", "Belizean", "Beninese", "Bermudian", "Bhutanese", "Bolivian", "Citizen of Bosnia and Herzegovina", "Botswanan", "Brazilian", "British", "British Virgin Islander", "Bruneian", "Bulgarian", "Burkinan", "Burmese", "Burundian", "Cambodian", "Cameroonian", "Canadian", "Cape Verdean", "Cayman Islander", "Central African", "Chadian", "Chilean", "Chinese", "Colombian", "Comoran", "Congolese", "Cook Islander", "Costa Rican", "Croatian", "Cuban", "Cymraes", "Cymro", "Cypriot", "Czech", "Danish", "Djiboutian", "Dominican", "Citizen of the Dominican Republic", "Dutch", "East Timorese", "Ecuadorean", "Egyptian", "Emirati", "English", "Equatorial Guinean", "Eritrean", "Estonian", "Ethiopian", "Faroese", "Fijian", "Filipino", "Finnish", "French", "Gabonese", "Gambian", "Georgian", "German", "Ghanaian", "Gibraltarian", "Greek", "Greenlandic", "Grenadian", "Guamanian", "Guatemalan", "Citizen of Guinea-Bissau", "Guinean", "Guyanese", "Haitian", "Honduran", "Hong Konger", "Hungarian", "Icelandic", "Indian", "Indonesian", "Iranian", "Iraqi", "Irish", "Israeli", "Italian", "Ivorian", "Jamaican", "Japanese", "Jordanian", "Kazakh", "Kenyan", "Kittitian", "Citizen of Kiribati", "Kosovan", "Kuwaiti", "Kyrgyz", "Lao", "Latvian", "Lebanese", "Liberian", "Libyan", "Liechtenstein citizen", "Lithuanian", "Luxembourger", "Macanese", "Macedonian", "Malagasy", "Malawian", "Malaysian", "Maldivian", "Malian", "Maltese", "Marshallese", "Martiniquais", "Mauritanian", "Mauritian", "Mexican", "Micronesian", "Moldovan", "Monegasque", "Mongolian", "Montenegrin", "Montserratian", "Moroccan", "Mosotho", "Mozambican", "Namibian", "Nauruan", "Nepalese", "New Zealander", "Nicaraguan", "Nigerian", "Nigerien", "Niuean", "Northern Irish", "Norwegian", "Omani", "Pakistani", "Palauan", "Palestinian", "Panamanian", "Papua New Guinean", "Paraguayan", "Peruvian", "Pitcairn Islander", "Polish", "Portuguese", "Prydeinig", "Puerto Rican", "Qatari", "Romanian", "Russian", "Rwandan", "Salvadorean", "Sammarinese", "Samoan", "Sao Tomean", "Saudi Arabian", "Scottish", "Senegalese", "Serbian", "Citizen of Seychelles", "Sierra Leonean", "Singaporean", "Slovak", "Slovenian", "Solomon Islander", "Somali", "South African", "South Sudanese", "Spanish", "Sri Lankan", "St Helenian", "St Lucian", "Sudanese", "Surinamese", "Swazi", "Swedish", "Swiss", "Syrian", "Taiwanese", "Tajik", "Tanzanian", "Thai", "Togolese", "Tongan", "Trinidadian", "Tristanian", "Tunisian", "Turkish", "Turkmen", "Turks and Caicos Islander", "Tuvaluan", "Ugandan", "Ukrainian", "Uruguayan", "Uzbek", "Vatican citizen", "Citizen of Vanuatu", "Venezuelan", "Vietnamese", "Vincentian", "Wallisian", "Welsh",
    "Korean", "French Polynesian", "New Caledonian", "Persian", "Arab", "Arabic", "Soviet"
}
COUNTRIES = {
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua", "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia", "Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina", "Burundi", "Cambodia", "Cameroon", "Canada", "Cape Verde", "Central African Rep", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", "Congo", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic", "Denmark", "Djibouti", "Dominica", "Dominican Republic", "East Timor", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Ivory Coast", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Kosovo", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Macedonia", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar,", "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "Norway", 
    "Oman", "Pakistan", "Palau", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russian Federation", "Rwanda", "St Kitts and Nevis", "St Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Swaziland", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Togo", "Tonga", "Trinidad and Tobago", "Trinidad", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe",
    "French Polynesia", "New Caledonia", "Korea", "Arabia"
}

ALL_ORIGINS = NATIONALITIES | COUNTRIES


def infer_origins():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        try:
            c.execute("ALTER TABLE translit ADD COLUMN origin TEXT")
        except sqlite3.OperationalError:
            c.execute("UPDATE translit SET origin = NULL")

        print("Step 1: Extracting word-category pairs with word boundary matching...")
        # DEBUG: Check ALL_ORIGINS
        print(f"  ALL_ORIGINS has {len(ALL_ORIGINS)} keywords")
        print(f"  Sample keywords: {list(ALL_ORIGINS)[:10]}")

        # Create temp table
        c.execute("""
            CREATE TEMP TABLE word_origin_matches (
                word TEXT,
                origin TEXT,
                match_count INTEGER
            )
        """)

        # Fetch all segmentations with categories
        c.execute("""
            SELECT segmentation, categories 
            FROM th_wikipedia 
            WHERE segmentation IS NOT NULL 
            AND categories IS NOT NULL
        """)

        batch = []
        processed = 0
        total_matches = 0  # DEBUG

        for segmentation, categories in c.fetchall():
            processed += 1
            if processed % 10000 == 0:
                print(
                    f"  Processed {processed} articles, found {total_matches} matches so far...")
                
            # Extract all [word] tokens
            words = re.findall(r'\[([^\]<>]+?)\]', segmentation)

            # DEBUG: First article
            if processed == 1:
                print(f"    Extracted words: {words[:5]}")

            # For each word, find which origins appear in categories (word boundary)
            for word in words:
                matched_origins = set()

                # Word boundary regex: origin must be standalone word
                for origin in ALL_ORIGINS:
                    # Match origin as whole word (case-insensitive)
                    pattern = r'\b' + re.escape(origin) + r'\b'
                    if re.search(pattern, categories):
                        matched_origins.add(origin)

                # Store each match
                for origin in matched_origins:
                    batch.append((word, origin, 1))
                    total_matches += 1

            # Batch insert
            if len(batch) >= 50000:
                print(f"    Inserting batch of {len(batch)} matches...")
                c.executemany(
                    "INSERT INTO word_origin_matches (word, origin, match_count) VALUES (?, ?, ?)",
                    batch
                )
                batch = []

        # Final batch
        if batch:
            print(f"    Inserting final batch of {len(batch)} matches...")
            c.executemany(
                "INSERT INTO word_origin_matches (word, origin, match_count) VALUES (?, ?, ?)",
                batch
            )

        print(f"  Total matches found: {total_matches}")
        conn.commit()

        print("Step 2: Aggregating matches per transliteration...")
        c.execute("""
            CREATE TEMP TABLE word_origin_summary AS
            SELECT 
                word,
                origin,
                SUM(match_count) as total_matches
            FROM word_origin_matches
            GROUP BY word, origin
        """)

        c.execute("CREATE INDEX idx_word_summary ON word_origin_summary(word)")

        c.execute("SELECT COUNT(DISTINCT word) FROM word_origin_summary")
        unique_words = c.fetchone()[0]
        print(f"  Covering {unique_words} unique words")

        print("Step 3: Ranking and selecting top origins...")

        # For each transliteration, get top 5 most frequent origins
        c.execute("""
            WITH ranked AS (
                SELECT 
                    t.id,
                    wos.origin,
                    wos.total_matches,
                    ROW_NUMBER() OVER (
                        PARTITION BY t.id 
                        ORDER BY wos.total_matches DESC, wos.origin
                    ) as rank
                FROM translit t
                JOIN word_origin_summary wos ON wos.word = t.thai
            )
            SELECT 
                id,
                GROUP_CONCAT(origin, ', ') as origins
            FROM ranked
            WHERE rank <= 5
            GROUP BY id
        """)

        results = c.fetchall()

        print(f"Step 4: Updating {len(results)} transliterations...")

        if results:
            c.executemany(
                "UPDATE translit SET origin = ? WHERE id = ?",
                [(origins, id) for id, origins in results if origins]
            )
            conn.commit()

        # Statistics
        c.execute("SELECT COUNT(*) FROM translit WHERE origin IS NOT NULL")
        with_origin = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM translit")
        total = c.fetchone()[0]

        print(f"\n{'='*60}")
        print(
            f"Origin coverage: {with_origin:,} / {total:,} ({100*with_origin/total:.1f}%)")
        print(f"{'='*60}")

        # Sample results
        c.execute("""
            SELECT thai, translit_of, origin 
            FROM translit 
            WHERE origin IS NOT NULL 
            ORDER BY RANDOM() 
            LIMIT 15
        """)
        print("\nSample results:")
        for thai, translit_of, origin in c.fetchall():
            print(f"  {thai} ({translit_of}): {origin}")
            
        
if __name__ == "__main__":
    infer_origins()
    
    # main()
    