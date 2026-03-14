from dict.scripts.paths import RAW_DIR, DB_PATH
from dict.scripts.utils import DEPENDENT_VOWELS, DIACRITICS, INDEPENDENT_VOWELS
from taibun import is_cjk
import re
import csv
import sqlite3

COVER_OOV = 0
COVER_CONTENT = 1
COVER_STOP = 2
COVER_TRANSLIT = 3

MAX_PREFIX_LEN = 23
MIN_COVERAGE_LEN = 3
MAX_TTC_LEN = 33

SHORT_HEADS = {"กฎ", "หอ", "ธง", "นก",
               # "จอ", "ชน", "ชา", 
               }

HEADS_TO_IGNORE = {"ที่", "คอน", "มิด", "อา", "บาร์", "แอร์", "มาส", "แชร์", "เตา",
                   "เอน", "เอก", "อัน", "พอล", "ฟอร์", "เชฟ", "ซูเปอร์", "ฟรี",
                   "โปร", "นิว", "ชิน", "วิน", "เซน", "วัน", "คิม", "มิส", "ปริ",
                   # "คริส", "เซอร์",
                   "อิส", "แฟร์", "หม่อ", "เจน", "ดับเบิล", "รัก", "อับ", "กับ",
                   "บัส", "ปริ", "บ้า", "เฟอร์", "เอล", "เอ็ด", "สติ", 
                   "สัน", "ยัน", "กอง", "จัน", "ปิยะ", "มัน", "คอม", "วิล", "จ้า",
                   "เดน", "แคน", "ดับ", "อิง", "ซัง", "รัต", "กาบ", "ลิง",
                   "อเล็กซา", "เตีย", "เสรี", "วิก", "คัน", "เลอ", "ยอด", "เรียว",
                   "บลู", "ทิม", "เซฟ", "ดอน", "เบอร์", "จ้า", "มหา", "มาร์",
                   "ตัน", "เอริ", "มานู"
                   }

LATIN_LETTER_NAMES = {
    "เอ", "บี", "ซี", "ดี", "อี", "เอฟ", "จี", "เอช", "ไอ", "เจ", "เค", "แอล", "เอ็ม", 
    "เอ็น", "โอ", "พี", "คิว", "อาร์", "เอส", "ที", "ยู", "วี", "ดับเบิลยู", "ดับเบิ้ลยู",
    "เอ็กซ์", "วาย", "ซี", "แซด", "เซด"
}

# The following surnames collide with real Thai words
CHI_KOR_SURNAMES = {
    "เจียง",  # 江, 姜 Jiang
    "เจี่ยง",  # 蔣 Jiang
    "เซียว", # Xiao
    "หยาง", # Yang
    "เจ้า", # Zhao, Chao
    "จอน", # Jeon
    "จัน", # Chan
    "หวง",  # 黄 Huang, Wong, Hwang (KR)
    "หม่า", # 馬 Ma
    "ว่าน", # Wan
    "จาง", # 張 Zhang, Chang, Cheung, 
    "หลิว", # Liu, Lau
    "เฉา", # Cao
    "ไป๋",  # 白 Bai
    "ไช่",  # Cai, Tsai (not a Thai word but very short)
    "ชัย",  # Chai
    "จิน", # Chen, Jin (KR)
    "ชิง",
    "พัก", # Park
    "อัน", # 安 An
    "พัน", # Pan
    "คัง", # Kang
    "วัง", # Wang (ZH/KR)
    "อี๋",  # 彝 Yi
    "ซอ",  # 서
    "อู๋",   # 吳 Wu, Ng
}

# These are Thai OOV words that should be included in the lexicon eventually
EXCEPTIONS = {
    "พระราชาณาจักร",  # Archaic spelling in "Royal Kingdom (of Cambodia)"
    # This is similar to the Buddha-sasana case

    "รัฏฐาภิบาล", # in GRUNK
    "ชาปัตตาเวีย",
    "สัทลักษณ์",
    "บรมวงศ์เธอ",
    'วรวงศ์เธอ',
    "นารวม", # collectivization
    "บรมพงศาภิมุข",
    "มูลวิวัติ", # radical
    "กงสะเด็น", # Picria
    "สิทธันต์", # dogma
    "โจราธิปไตย", # kleptocracy (sandhi case: โจร + อาธิปไตย)
    "จตุราธิปไตย", # tetrarchy (sandhi case: จตุรา + อาธิปไตย)
    "ชราธิปไตย", # gerontocracy (sandhi case: ชรา + อาธิปไตย)
    "นาวิกานุภาพ", # naval power (sandhi case: นาวิก + อานุภาพ)
    "เสนาธิปไตย", # military dictatorship (sandhi case: เสนา + อาธิปไตย)
    "โลกิยานุวัติ", # secularization (sandhi case: โลกิ + อานุวัติ)
    "สันสกฤตาภิวัตน์", # Sanskritization (sandhi case: สันสกฤต + อภิวัตน์)
    "เสนาธิปัตย์",  # Chief of Staff (sandhi case: เสนา + อาธิปัตย์)
    'อนุชาธิราช', # younger brother of the king (sandhi case: อนุชา + อาธิราช)
    "กนิษฐาธิราช", # younger sister of the king (sandhi case: กนิษฐา + อาธิราช)
    "พัชราภิเษก", # Diamond Jubilee (sandhi case: พัชรา + อภิเษก)
    "สรรพาวุธ",  # ordnance; artillery (sandhi case: สรรพ + อาวุธ)
    "อัคราธิการ",  # archduke (sandhi case: อัคร- + อธิการ)
    "บรมราชานุสรณ์", # royal monument (sandhi case: บรมราชา + อนุสรณ์)
    "บรมราชานุสาวรีย์", # royal monument (sandhi case: บรมราชา + อนุสาวรีย์)
    "ศาสนาธิปไตย", # theocracy (sandhi case: ศาสนา + อาธิปไตย)
    
    # Buddhist fellowship (phút•tháˀ sàat•sa•ník•ka•sàm•pan)
    "พุทธศาสนิกสัมพันธ์",

    "มุรธาธร",  # Royal secretariat
    "วิสาหกร", # entrepreneur
    "แม่หยัว",  # title for a royal woman
    
    "สถาปัตยสวนศาสตร์", # architectural acoustics
    "ศิษยาภิบาล",  # pastor (sandhi case: ศิษย์ + อภิบาล)
    "ปูชนียสถาน",
    'ปิตุจฉา',
    "วิมาดา",
    'โอรสาธิราช',
    "อันดับย่อยเต่าคองู",
    "สหโภชน์", # Steward
    "วิมัย", # Exchange, reciprocity, barter (from Skt/Pali "vimaya")
    "เทศวิวัตน์", # localization
    "ปดิวรัดา",
    "หนานเฉาเหว่ย",  # Gymnanthemum extensum
    "เห่", # a type of song
    "เบิ้ม", # big (colloquial)
    "คริสตจักร", # Christendom
    "ปรเมนทร", # alt spelling in royal titles
    "สรรพันตรเทวนิยม", # panentheism
    "พิพัฒนาการนิยม", # progressivism
    "พญาอนันตนาคราช", # serpent god or something like that
    "อติสีตชีววิทยา", # cryobiology
    "มีสกุล", # noble, aristocratic, genteel (from Skt/Pali "sakulya" with prefix "มี-")
    "มิตราภรณ์", #
    "ขีปน", # ballistic (prefix)
    "กาละ", # time (from Skt/Pali "kala")
    "กะเลิง", # Kaloeng ethnic group
    "พักๆ", # intermittent
    "รัก ๆ เลิก ๆ", # on again, off again (relationship)
    "เรขลักษณ์", # geometric charge (heraldry)
    "ส้มกบ", # Creeping Lady's sorrel
}


class Lexicon:
    def __init__(self, nouns_only=False):
        self.base = {}
        self.base_propn = {}
        self.short_prefixes = set()
        self.latin_letters = []
        self.transliterations = {}
        self.safe_titles = set()
        self.load(nouns_only=nouns_only)

    def load(self, nouns_only=False):
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()

            # First pass: Load Volubilis (has good freq data)
            if nouns_only:
                c.execute("""
                    SELECT thai, variants, freq FROM volubilis
                    WHERE pos IN ('n.', 'n. exp.', 'adj.')
                """)
            else:
                c.execute("""
                    SELECT thai, variants, freq FROM volubilis
                    WHERE pos NOT IN ('symb.', 'interj.')
                    AND NOT (thai LIKE '%.' AND LENGTH(thai) < 3)
                """)

            for (thai, variants, freq) in c.fetchall():
                word = thai.strip("-")
                if thai in LATIN_LETTER_NAMES:
                    continue
                self.base[word] = max(freq or 0, self.base.get(word, 0))
                if variants:
                    for variant in variants.split(" = "):
                        for v in variant.split(" ; "):
                            self.base[v.strip()] = max(freq or 0, self.base.get(v, 0))

            c.execute("""
                SELECT REPLACE(thai, '-', '') AS no_hyphen FROM volubilis
                WHERE pos = 'pref.' AND LENGTH(no_hyphen) < 3
                UNION
                SELECT REPLACE(word, '-', '') AS no_hyphen FROM th_wiktionary
                WHERE pos = 'prefix' AND LENGTH(no_hyphen) < 3
            """)
            self.short_prefixes = {row[0] for row in c.fetchall()}

            # Load proper nouns separately as well
            c.execute("""
                SELECT thai FROM volubilis
                GROUP BY thai
                    HAVING COUNT(CASE WHEN pos = 'n. prop.' THEN 1 END) > 0
                    AND COUNT(CASE WHEN pos != 'n. prop.' THEN 1 END) = 0
                UNION
                SELECT word FROM th_wiktionary
                WHERE pos = 'proper noun'
            """)
            for (thai,) in c.fetchall():
                if thai in LATIN_LETTER_NAMES:
                    continue
                self.base_propn[thai] = 0
                if not nouns_only:
                    self.base[thai] = 0

            if not nouns_only:
                c.execute("""
                    SELECT thai FROM see_also WHERE LENGTH(thai) > 3
                    UNION
                    SELECT word FROM th_wiktionary 
                    WHERE LENGTH(word) >= 3
                    AND (roman LIKE '%•%' OR roman LIKE '% %')
                    UNION
                    SELECT o.thai FROM thai_oov o
                """)

                for (thai,) in c.fetchall():
                    word = thai.strip("-")
                    if word not in self.base:
                        self.base[word] = 0

            self.latin_letters = sorted(list(LATIN_LETTER_NAMES), key=len, reverse=True)

            # Add transliterations
            with open(RAW_DIR / f"transliterations.tsv", "r") as f:
                reader = csv.reader(f, delimiter="\t")
                next(reader)
                self.transliterations.update({row[0]: row[1] for row in reader})

            with open(RAW_DIR / f"safe_titles.txt", "r") as f:
                self.safe_titles.update({line.strip() for line in f})

    def get_prefix_words(self, text, include_translit=True):
        """Get all lexicon words that appear at the start of text."""
        words = []
        
        for end in range(MIN_COVERAGE_LEN, min(len(text), MAX_PREFIX_LEN) + 1):
            remainder = text[end:] + "  "
            if remainder[0] in DEPENDENT_VOWELS + DIACRITICS:
                continue
            if remainder[1] == "\u0E4C":
                continue

            candidate = text[:end]
            if candidate in HEADS_TO_IGNORE | LATIN_LETTER_NAMES:
                continue
            elif " " in candidate:
                continue
            elif candidate in CHI_KOR_SURNAMES:
                continue
            elif candidate in self.base_propn:
                continue
            elif candidate in self.base:
                words.append(candidate)
            elif include_translit and candidate in self.transliterations:
                words.append(candidate)

        if not words and text[:2] in SHORT_HEADS and text[:2] not in CHI_KOR_SURNAMES:
            remainder = text[2:] + "  "
            if remainder[1] == "\u0E4C":
                return words
            words.append(text[:2])
            
        return words

    def coverage_mask(self, text, include_translit=False, debug=False):
        """
        Return a mask indicating which positions are covered by Thai words in the lexicon,
        and a list of (word, start, end) for each word.
        Uses DP to find optimal segmentation with minimal cuts.
        0 = OOV, 1 = covered by Thai word, 2 = boundary (space/hyphen), 3 = covered by transliteration
        """
        n = len(text)
        mask = [COVER_OOV] * n
        words = []

        def _is_valid_start(pos):
            """Check if position can be the start of a word."""
            if pos >= n:
                return False
            ch = text[pos]
            if ch in DIACRITICS + DEPENDENT_VOWELS:
                return False
            if pos > 0 and text[pos - 1] in INDEPENDENT_VOWELS:
                return False
            if pos > 0 and text[pos - 1] == "\u0E31":  # linking short "a"
                return False
            return True

        def _is_valid_end(pos):
            """Check if position can be the end of a word (exclusive)."""
            if pos > n:
                return False
            remainder = text[pos:] + "  "
            if remainder[0] in DEPENDENT_VOWELS + DIACRITICS:
                return False
            if remainder[1] == "\u0E4C":
                return False
            return True
        
        def _global_dp(allow_short=True):
            """
            Global DP over entire string.
            Returns: (oov_chars, segments, short_chars, path)
            """

            INF = float("inf")

            # dp[i] = (oov_chars, segments, short_chars, path)
            dp = [(INF, INF, INF, []) for _ in range(n + 1)]
            dp[0] = (0, 0, 0, [])

            for i in range(n):
                base_oov, base_segs, base_short, base_path = dp[i]
                if base_oov == INF:
                    continue

                # Skip STOP positions (already fixed boundaries)
                if mask[i] == COVER_STOP:
                    if dp[i] < dp[i + 1]:
                        dp[i + 1] = dp[i]
                    continue

                # Try lexicon words
                for j in range(i + 1, min(n, i + MAX_TTC_LEN) + 1):

                    if not _is_valid_start(i):
                        continue
                    if not _is_valid_end(j):
                        continue

                    candidate = text[i:j]
                    length = j - i

                    if candidate == "วา" and text[i:].startswith("วาย"):
                        continue  # common OOV chunk that causes issues

                    is_base = candidate in self.base
                    is_translit = include_translit and candidate in self.transliterations
                    is_propn = candidate in self.base_propn
                    is_short_prefix = candidate in self.short_prefixes
                    is_short_exception = candidate in ["ใน", "ณ", "ที่", "ปี"]  # always allow

                    is_valid_word = is_base or is_propn or is_translit

                    if is_short_exception:
                        pass
                    elif not is_valid_word and not (allow_short and is_short_prefix):
                        continue
                    elif length == 1:
                        continue
                    
                    is_short = (
                        length < MIN_COVERAGE_LEN
                        and not is_translit
                        and not is_short_prefix
                        and not is_short_exception
                    )

                    if is_short and not allow_short and not is_short_exception:
                        continue

                    new_tuple = (
                        base_oov,
                        base_segs + 1,
                        base_short + (length if is_short else 0),
                        base_path + [(candidate, i, j, is_translit)]
                    )

                    if new_tuple[:3] < dp[j][:3]:
                        dp[j] = new_tuple

                # OOV fallback (single char)
                new_tuple = (
                    base_oov + 1,
                    base_segs,
                    base_short,
                    base_path
                )

                if new_tuple[:3] < dp[i + 1][:3]:
                    dp[i + 1] = new_tuple

            return dp[n]

        def _fill_latin_letters():
            """Fill Latin letter names (เอ, บี, ซี, etc.)"""
            for letter in self.latin_letters:
                for m in re.finditer(re.escape(letter), text):
                    start, end = m.start(), m.end()
                    if not _is_valid_start(start) or not _is_valid_end(end):
                        continue
                    if all(mask[k] == COVER_OOV for k in range(start, end)):
                        for k in range(start, end):
                            mask[k] = COVER_CONTENT
                        words.append((letter, start, end, False))

        # === MARK BOUNDARIES ===
        # But allow transliterations to cross space and hyphen boundaries
        for i, ch in enumerate(text):
            if ch in "():;,/–−—!×'☆~\"½*+@?%&¹★…":
                mask[i] = COVER_STOP
            elif re.match(r"[A-Za-z0-9๑-๙ฯ]", ch):
                mask[i] = COVER_STOP
            elif is_cjk(ch):
                mask[i] = COVER_STOP

        # === MAIN GLOBAL DP SEGMENTATION ===
        # Run full DP (allow short words)
        oov_chars, segs, short_chars, path = _global_dp(allow_short=True)

        short_ratio = short_chars / n if n > 0 else 0

        if text in self.safe_titles:
            pass
        elif short_ratio >= 0.16:
            if debug:
                print(
                    f"  Rejecting shorts-heavy segmentation "
                    f"({short_ratio:.1%}), falling back to no-shorts"
                )

            oov_chars_ns, segs_ns, short_chars_ns, path_ns = _global_dp(
                allow_short=False)

            # Always use no-shorts if short ratio too high
            # (even if it means marking everything as OOV)
            oov_chars, segs, short_chars, path = (
                oov_chars_ns, segs_ns, short_chars_ns, path_ns
            )

        if debug:
            print(
                f"Best → {oov_chars} OOV, "
                f"{segs} segs, "
                f"{short_chars} short "
                f"({short_chars/n:.1%})"
            )

        # Apply best path to mask
        for word, start, end, is_translit in path:
            mask_val = COVER_TRANSLIT if is_translit else COVER_CONTENT
            for k in range(start, end):
                mask[k] = mask_val

        words.extend(path)

        # === FINALIZE BOUNDARIES ===
        for i, ch in enumerate(text):
            if ch in ".- " and mask[i] == COVER_OOV:
                mask[i] = COVER_STOP

        # === FILL LATIN LETTERS ===
        _fill_latin_letters()

        # Strip is_translit flag from words for return value
        words = [(w, s, e) for w, s, e, *_ in words]

        return mask, words
    
    def explains(self, span, include_translit=False, debug=False):
        """
        Does the base lexicon completely cover the target span?
        
        Args:
            span: Text to check coverage for
            include_translit: If True, also consider transliterations as valid coverage
            debug: Print debug information
        
        Returns:
            True if span is fully covered (no OOV positions remaining)
        """
        mask, _ = self.coverage_mask(span, include_translit=include_translit, debug=debug)
        return all(m != COVER_OOV for m in mask)
    

    def coverage_to_string(self, text, words, mask):
        spans = []
        covered = []
        for w, s, e in sorted(words, key=lambda x: len(x[0]), reverse=True):
            # Reject any overlaps
            if any(not (e <= cs or s >= ce) for cs, ce in covered):
                continue
            spans.append((w, s, e, "known"))
            covered.append((s, e))
        spans.extend((text[i:i+1], i, i+1, "stop")
                    for i in range(len(text)) if mask[i] == COVER_STOP)
        spans.sort(key=lambda s: s[1])

        cur_pos = 0
        output = ""
        for w, s, e, status in spans:
            if s > cur_pos:
                latest = text[cur_pos:s]
                if cur_pos == 0 and latest in SHORT_HEADS:
                    output += f"[{latest}]"
                else:
                    output += f"<{latest}>"
            if status == "stop":
                output += w
            elif status == "known":
                output += f"[{w}]"
            cur_pos = e
        if cur_pos < len(text):
            output += f"<{text[cur_pos:]}>"
        return output


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: lexicon.py text")
        sys.exit(1)
    
    lexicon = Lexicon()
    text = sys.argv[1]

    # prefixes = lexicon.get_prefix_words(text, include_translit=False)
    # print(prefixes)

    mask, words = lexicon.coverage_mask(
        text, include_translit=True, debug=True)

    # print("\nWords detected:")
    # for w, s, e in words:
    #     print(f"  {w} [{s}:{e}]")

    # print("\nVisualization:")
    # visualize_mask(text, mask)

    # print("\nFully covered?", all(m != COVER_OOV for m in mask))

    print(lexicon.coverage_to_string(text, words, mask))

    # Sandhi check
    # lexicon = Lexicon()
    # joinable_words = {"า" + word[1:] for word in lexicon.base if 
    #             len(word) > 3 and
    #             word.startswith("อ") and word[1] not in DIACRITICS + DEPENDENT_VOWELS}
    # for translit in lexicon.transliterations:
    #     if any(translit.endswith(joinable) for joinable in joinable_words):
    #         print(translit)