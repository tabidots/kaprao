from dict.scripts.paths import RAW_DIR, DB_PATH
import sqlite3
import re
import csv
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from pythainlp.tokenize import syllable_tokenize
from dict.scripts.phonetic_utils import ipa_to_aua, spell_out_alphanum, capitalize, reconstruct_from_syllables

# # Load UMT5 model once at startup
print("Loading UMT5 model...")
tokenizer = AutoTokenizer.from_pretrained("B-K/umt5-thai-g2p-v2-0.5k")
model = AutoModelForSeq2SeqLM.from_pretrained("B-K/umt5-thai-g2p-v2-0.5k")
print("Model loaded!")

# A rough approximation of Thai phonotactics for syllable counting in toneless
SYLLABLE_RE = re.compile(
    r"(?:[kp]h?l?|[kp]h?r?|t[hr]?|ch|ng|[bdf]r?|[hjlmnrswy])?[aiueoāīūēōøǿAIUEOĀĪŪĒŌØǾ]+(?:ng|[lmnsptk])?",
    flags=re.IGNORECASE
)


def count_syllables_in_roman(ipa):
    """Count syllables in IPA output."""
    if not ipa:
        return 0
    return len([s for s in ipa.split('•') if s])


def get_word_shape(toneless):
    """
    Extract word and syllable structure from toneless romanization.
    Returns list of dicts with info about each syllable.
    """
    if not toneless:
        return None

    # Track word starts
    word_start_indexes = [0]
    last_c = toneless[0]
    for i, char in enumerate(toneless[1:], start=1):
        if last_c == " ":
            word_start_indexes.append(i)
        if last_c == "-" and char not in "aiueoāīūēōøǿAIUEOĀĪŪĒŌØǾ":
            word_start_indexes.append(i)
        last_c = char

    # Extract syllable info
    syllables = SYLLABLE_RE.finditer(toneless)
    syllable_info = []
    for syl in syllables:
        start = syl.start()
        syllable_info.append({
            "syllable": syl.group(0),
            "is_first": start == 0,
            "comes_after_hyphen": start > 1 and toneless[start - 1] == "-" and toneless[start] not in "aiueoāīūēōøǿAIUEOĀĪŪĒŌØǾ",
            "starts_new_word": start in word_start_indexes,
            "is_capitalized": syl.group(0).lower() != syl.group(0)
        })

    return syllable_info


def apply_word_shape(ipa, syllable_info):
    """
    Apply word shape (capitalization, spacing, hyphens) to IPA syllables.
    
    Args:
        ipa: String with syllables separated by '.'
        syllable_info: List of dicts from get_word_shape()
    
    Returns:
        Formatted romanization string
    """
    if not syllable_info:
        return None

    # Split IPA into syllables
    ipa_syllables = [s for s in re.split(r"[•\s]", ipa) if s]

    if len(ipa_syllables) != len(syllable_info):
        return None

    roman = ""
    for syl, syl_info in zip(ipa_syllables, syllable_info):
        # Apply capitalization
        if syl_info["is_capitalized"]:
            syl = capitalize(syl)

        # Add separator based on position
        if syl_info["is_first"]:
            pass
        elif syl_info["comes_after_hyphen"]:
            roman += "-"
        elif syl_info["starts_new_word"]:
            roman += " "
        else:
            roman += "•"

        roman += syl

    return roman.strip()


def get_ipa(thai_word):
    """
    Romanize Thai word using UMT5 G2P model.
    
    Returns:
        IPA string with syllables separated by periods.
    """
    try:
        inputs = tokenizer(thai_word, return_tensors="pt",
                           padding=True, truncation=True)
        outputs = model.generate(**inputs, num_beams=3, max_new_tokens=256)
        phonemes = tokenizer.decode(outputs[0], skip_special_tokens=True)
        phonemes = phonemes.replace(' ', '')
        phonemes = phonemes.replace("bɔː˧.ri˦˥.tit̚˨˩", "bri˨˩.tit̚˨˩")
        return phonemes
    except Exception as e:
        print(f"Failed to romanize {thai_word}: {e}")
        return None


def process_entry(thai, variants, toneless):
    """
    Process a single entry and return romanization results.
    
    Returns:
        dict with keys: 'ipa', 'roman', 'needs_check', 'flag_reason'
    """
    result = {
        'ipa': None,
        'roman': None,
        'needs_check': 1,
        'flag_reason': None
    }

    # Handle prefix/suffix markers
    is_prefix, is_suffix = False, False
    working_thai = thai
    working_toneless = toneless.split(" = ")[0]

    if toneless and toneless.startswith("-"):
        is_suffix = True
        working_toneless = working_toneless[1:]
        working_thai = thai.lstrip("-")
    elif toneless and toneless.endswith("-"):
        is_prefix = True
        working_toneless = working_toneless[:-1]
        working_thai = thai.rstrip("-")

    # Spell out alphanumeric characters
    if re.search(r"[0-9A-Za-z]", working_thai):
        working_thai = spell_out_alphanum(working_thai, variants)

    # Get IPA from UMT5
    # Some headwords need a bit of a nudge to output the right result
    if working_thai == "วัดมหาธาตุยุวราชรังสฤษฎิ์ราชวรมหาวิหาร":
        working_thai = "วัด มหาธาต ยุวราชรังสฤษฎิ์ ราช วรมหาวิหาร"
    if working_thai == "หม่อมเจ้าจุลเจิม ยุคล":
        ipa = get_ipa("หม่อมเจ้าจุลเจิม ยุ") + "." + get_ipa("คน")
        ipa = ipa.replace("ʔ", "")
    else:
        ipa = get_ipa(working_thai)

    # Rescue some cases where UMT5 fails
    if working_toneless.endswith("a") and re.search(r"a[˩˨˧˦˥]+\.$", ipa):
        ipa = ipa[:-1]
    elif ipa.endswith("."):
        syllables = syllable_tokenize(thai)
        ipa = ".".join([get_ipa(syllable) for syllable in syllables])
    elif toneless.endswith("a-") and not thai.endswith("ะ-"):
        # These will still need to be reviewed manually
        ipa = get_ipa(thai.replace("-", "ะ-"))
        # Sometimes UMT5 adds a syllable starting with h
        if m := re.search(r"\.h[^\.]+$", ipa):
            ipa = ipa.replace(m.group(), "")
        
    result['ipa'] = ipa # if not ipa, result['flag_reason'] = 'umt5_failed' & return
    roman = ipa_to_aua(ipa) # if not roman, result['flag_reason'] = 'umt5_failed' & return

    # Other times, it changes or misinterprets the last syllable
    if toneless.endswith("a-") and not re.search(r"aʔ?[˩˨˧˦˥]+$", ipa):
        result['flag_reason'] = 'umt5_failed'
        return result
    
    # Determine if we need word shape matching
    if re.search(r'\s|ๆ|-|\.', working_thai) or ' ' in working_toneless:
        syllable_info = get_word_shape(working_toneless)

        # Check syllable count
        roman_syll_count = count_syllables_in_roman(roman)
        toneless_syll_count = len(syllable_info)
        if roman_syll_count != toneless_syll_count:
            try:
                roman = reconstruct_from_syllables(working_thai, toneless_syll_count)
            except Exception as e:
                result['flag_reason'] = 'syllable_mismatch'
                return result
            ipa = None

        # Apply word shape
        roman = apply_word_shape(roman, syllable_info)
        if not roman:
            result['flag_reason'] = 'shape_application_failed'
            return result
        
    elif working_toneless and working_toneless[0].isupper():
        roman = capitalize(roman)

    # Restore prefix/suffix markers
    if is_suffix:
        roman = "-" + roman
    if is_prefix:
        roman += "-"

    result['roman'] = roman
    result['needs_check'] = 0

    return result


def main():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # First pass: Get Wiktionary romanizations for single-word headwords
        print("Filling in romanizations from Wiktionary...")
        c.execute("""
            SELECT v.id, v.thai, v.toneless, tw.roman
            FROM volubilis v
            LEFT JOIN (
                SELECT word, MIN(id) as min_id
                FROM th_wiktionary
                GROUP BY word
            ) first_tw ON first_tw.word = v.thai
            LEFT JOIN th_wiktionary tw ON tw.id = first_tw.min_id
            WHERE pron_src = 'wiktionary' 
            -- v.needs_check_romanization = 1
            AND tw.roman IS NOT NULL
        """)
        results = c.fetchall()
        total = len(results)

        batch = []
        for (id, _, toneless, roman) in results:
            new_roman = []
            for roman_variant in roman.split(" = "):
                if toneless == capitalize(toneless):
                    new_roman.append(capitalize(roman_variant))
                else:
                    new_roman.append(roman_variant)
            batch.append((' = '.join(new_roman), id))

            if len(batch) >= 1000:
                c.executemany("""
                    UPDATE volubilis 
                    SET
                        roman = ?, needs_check_romanization = 0, 
                        pron_src = 'wiktionary', flag_reason = NULL 
                    WHERE id = ?
                """, batch)
                conn.commit()
                print(f"Processed {len(batch)} Wiktionary entries...")
                batch = []

        if batch:
            c.executemany("""
                    UPDATE volubilis 
                    SET
                        roman = ?, needs_check_romanization = 0, 
                        pron_src = 'wiktionary', flag_reason = NULL 
                    WHERE id = ?
                """, batch)
            conn.commit()
            print(f"Processed {len(batch)} Wiktionary entries. Done!")

        print("Adjusting word shapes for those romanizations...")
        c.execute("""
            SELECT id, thai, toneless, roman FROM volubilis
            WHERE pron_src = 'wiktionary'
            AND (thai LIKE '% %'
                OR thai LIKE '%ๆ%'
                OR (thai LIKE '%-%' AND thai NOT LIKE '%-')
                OR toneless LIKE '% %')
        """)
        batch = []
        for id, thai, toneless, roman in c.fetchall():
            toneless_variants = {v: get_word_shape(
                v) for v in toneless.split(" = ")}

            new_roman = []
            for roman_variant in roman.split(" = "):
                roman_syll_count = len(
                    re.split(r"(?<=.)[-•\s]", roman_variant))
                target_toneless = next((k for k, v in toneless_variants.items()
                                        if len(v) == roman_syll_count), None)

                new_roman_variant = None
                if target_toneless:
                    new_roman_variant = apply_word_shape(
                        roman_variant, toneless_variants[target_toneless])
                if new_roman_variant and new_roman != roman:
                    new_roman.append(new_roman_variant)
                else:
                    new_roman.append(roman_variant)
            new_roman = " = ".join(new_roman)
            
            # Weird bug
            if new_roman.startswith("•"):
                new_roman = new_roman[1:]

            if new_roman != roman:
                batch.append((new_roman, id))

        c.executemany("""
            UPDATE volubilis 
            SET roman = ?
            WHERE id = ?
        """, batch)
        conn.commit()
        print("Done!")

        print("Filling in hardcoded romanizations...")
        with open(RAW_DIR / "hardcoded-roman.tsv", "r") as f:
            reader = csv.reader(f, delimiter="\t")
            HARDCODED_ROMAN = dict(reader)

        for k, v in HARDCODED_ROMAN.items():
            c.execute("""
                UPDATE volubilis
                SET roman = ?, needs_check_romanization = 0, 
                    flag_reason = NULL, pron_src = 'manual'
                WHERE thai = ? AND 
                      (english <> 'est Cola' OR english IS NULL)
                      AND needs_check_romanization = 1
            """, (v, k))
        conn.commit()
        print("Done!")

        # Second pass: Use UMT5 for remaining entries
        print("\nProcessing remaining entries with UMT5...")
        c.execute("""
            SELECT id, thai, variants, toneless FROM volubilis
            WHERE needs_check_romanization = 1;
        """)
        results = c.fetchall()
        total = len(results)
        print(f"Total entries to process: {total}")

        batch = []
        count = 0
        flagged_count = 0

        for (id, thai, variants, toneless) in results:
            result = process_entry(thai, variants, toneless)

            if result['ipa']:
                if result['needs_check'] == 0:
                    # Success
                    batch.append((result['ipa'], result['roman'], 0, None, id))
                else:
                    # Flagged for review
                    batch.append(
                        (result['ipa'], None, 1, result['flag_reason'], id))
                    flagged_count += 1
            else:
                # Complete failure
                batch.append((None, None, 1, result['flag_reason'], id))
                flagged_count += 1

            if len(batch) >= 200:
                count += len(batch)
                c.executemany("""
                    UPDATE volubilis 
                    SET 
                        ipa = ?, roman = ?, needs_check_romanization = ?, 
                        pron_src = 'umt5', flag_reason = ?
                    WHERE id = ?
                """, batch)
                conn.commit()
                print(
                    f"Processed {count} / {total} entries ({count/total*100:.1f}%)...")
                batch = []

        if batch:
            count += len(batch)
            c.executemany("""
                    UPDATE volubilis 
                    SET 
                        ipa = ?, roman = ?, needs_check_romanization = ?, 
                        pron_src = 'umt5', flag_reason = ?
                    WHERE id = ?
                """, batch)
            conn.commit()
            print(f"Processed {count} / {total} entries. Done!")

        # Fixing prefixes
        c.execute("""
            SELECT id, roman FROM volubilis
            WHERE pos = 'pref.' AND roman NOT LIKE '%-'
            """)
        batch = []
        for (id, roman) in c.fetchall():
            new_roman = []
            for variant in roman.split(" = "):
                new_roman.append(variant + "-")
            new_roman = " = ".join(new_roman)
            batch.append((new_roman, id))
        c.executemany("""
            UPDATE volubilis 
            SET roman = ?
            WHERE id = ?
        """, batch)
        conn.commit()

        # Final stats
        c.execute(
            "SELECT COUNT(*) FROM volubilis WHERE needs_check_romanization = 1")
        remaining = c.fetchone()[0]

        c.execute(
            "SELECT COUNT(*) FROM volubilis WHERE needs_check_romanization = 0")
        completed = c.fetchone()[0]

        print(f"\n=== Final Statistics ===")
        print(f"Completed: {completed}")
        print(f"Flagged for review: {flagged_count}")
        print(f"Still needs work: {remaining}")

        # Show breakdown of flag reasons
        c.execute("""
            SELECT flag_reason, COUNT(*) 
            FROM volubilis 
            WHERE flag_reason IS NOT NULL 
            GROUP BY flag_reason
        """)
        print(f"\nFlag reasons:")
        for reason, count in c.fetchall():
            print(f"  {reason}: {count}")


if __name__ == "__main__":
    main()