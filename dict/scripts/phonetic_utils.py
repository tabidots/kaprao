from unicodedata import normalize
from pythainlp.transliterate import transliterate, pronunciate
from pythainlp.tokenize import syllable_tokenize
import re
import csv

# Volubilis tone notation puts the following symbols before each syllable
# syllables may run together or be separated by spaces, so we should preserve the spaces

VOLUBILIS_TONES = {
    "-": "mid",
    "\\": "falling",
    "/": "rising",
    "_": "low",
    "¯": "high",
}

VOLUBILIS_VOWELS = {
    "Eūa": "Ʉa",
    "eūa": "ʉa",
    "eūoe": "ʉa",
    "Eūoe": "Ʉa",
    "Eū-oe": "Ʉa",
    "eū-oe": "ʉa",
    "Eū": "Ʉʉ",
    "eū": "ʉʉ",
    "Eu": "Ʉ",
    "eu": "ʉ",
    "īa": "ia",
    "īe": "ia",
    "Īa": "Ia",
    "Īe": "Ia",
    "ĪE": "ia", # only in the word ASEAN
    "ūa": "ua",
    "ua": "ua",
    "Ūa": "Ua",
    "Ua": "Ua",
    "Iū": "iw",
    "Iu": "iw",
    "iū": "iw",
    "iu": "iw",
    "īo": "iaw",
    "āo": "aaw",
    "Āo": "Aaw",
    "Aē": "Ɛɛ",
    "aē": "ɛɛ",
    "Ae": "Ɛ",
    "ae": "ɛ",
    "Oē": "Əə",
    "oē": "əə",
    "Oe": "Ə",
    "oe": "ə",
    "Ø": "Ɔɔ",
    "ø": "ɔɔ",
    "Ǿ": "Ɔ",
    "ǿ": "ɔ",
    "ā": "aa",
    "Ā": "Aa",
    "ī": "ii",
    "Ī": "Ii",
    "ū": "uu",
    "Ū": "Uu",
    "ē": "ee",
    "Ē": "Ee",
    "ō": "oo",
    "Ō": "Oo",
    "əi": "əy",
    "Əi": "Əy",
    "eo": "ew",
    "ɛo": "ɛw",
    "Eo": "Ew",
}

ASCIIFY = {
    "ā": "a",
    "Ā": "A",
    "ī": "i",
    "Ī": "I",
    "ū": "u",
    "Ū": "U",
    "ē": "e",
    "Ē": "E",
    "ō": "o",
    "Ō": "O",
    "Ǿ": "O",
    "ǿ": "o",
    "Ø": "O",
    "ø": "o",
}

TLTK_NOTATION = {
    # Order is important here
    "j": "y",
    "@": "ə",
    "O": "ɔ",
    "x": "ɛ",
    "U": "ʉ",
    "N": "ng",
    "ch": "CH",
    "c": "j",
    "CH": "ch",
    "?": "ˀ",
    "aj": "ai", # this will never get replaced
    "iia": "ia",
    "ʉʉa": "ʉa",
    "uua": "ua",
}


TLTK_TONES = {
    "0": "mid",
    "1": "low",
    "2": "falling",
    "3": "high",
    "4": "rising",
}

TONE_MARKS = {
    "mid": "",
    "falling": "\u0302",
    "rising": "\u030C",
    "low": "\u0300",
    "high": "\u0301",
}

IPA_TONES = {
    "˧": "mid",
    "˨˩": "low",
    "˦˥": "high",
    "˩˩˦": "rising",
    "˥˩": "falling",
    "˦˩": "falling"
}

IPA_REPLACEMENTS = {
    "j": "y",
    "t͡ɕʰ": "ch",
    "t͡ɕ": "j",
    "ʰ": "h",
    "ɤ": "ə",
    "ʔ": "ˀ",
    "ɯ": "ʉ",
    "\u031a": "",
    "\u032f": "",
    "ŋ": "ng"
}

SHORT_DIPHTHONG_WORDS = {
    "ผัวะ",
    "จั๊วะ",
    "ขาวจั๊วะ",
    "เจี๊ยะ",
    "เกี๊ยะ",
    "เกี๊ยะดำ",
    "เกี๊ยะเปลือกบาง",
    "เกี๊ยะเปลือกแดง",
    "กอเอี๊ยะ",
    "แป๊ะเจี๊ยะ",
    "ปอเปี๊ยะ",
    "เปาะเปี๊ยะ",
    "ปอเปี๊ยะกุ้ง",
    "ปอเปี๊ยะสด",
    "ปอเปี๊ยะทอด"
}

VOWELS = re.compile(r"([aeiouáàǎâèéêěìíîǐòóôǒùúûǔ]|[ɔəɛʉ][\u0300\u0301]?)", flags=re.IGNORECASE)
NEEDS_GLOTTAL_STOP = re.compile(r"([bdfghjklmnprstwyˀ](?:[àáèéìíòóùú]|[ɔəɛʉ][\u0300\u0301]))(?=\s|$)", flags=re.IGNORECASE)
NEEDS_GLOTTAL_STOP_DIPH = re.compile(r"([iìíîǐuúùûǔ]a|ʉ[\u0300\u0301]a)(?=\s|$)", flags=re.IGNORECASE)
INDIAN_NAMES_DRA = re.compile(
    r"(?<=[bdfghjklmnprstwy])[áà]•([bdfghjklmnprstwy])([êěèée]+)t•ráˀ(?=\s|$)") # -> \2\1thráˀ


def replace_repeater(input):
    return re.sub(r"(\S+)\s?ๆ", r"\1 \1", input)

def add_tone_mark(syl, which_tone):
    try:
        first_vowel_idx = VOWELS.search(syl).start()
    except AttributeError:  # no vowel
        return syl
    
    tone_mark = TONE_MARKS[which_tone]
    syl = syl[:first_vowel_idx + 1] + tone_mark + syl[first_vowel_idx + 1:]
    syl = normalize("NFC", syl)
    if first_vowel_idx == 0:
        syl = "ˀ" + syl

    return syl


def capitalize(s):
    has_glottal_stop = False
    if s.startswith("ˀ"):
        s = s[1:]
        has_glottal_stop = True
    result = s[0].upper() + s[1:]
    if has_glottal_stop:
        result = "ˀ" + result
    return result


def make_plain(s):
    """Converts a Volubilis full phonetic transcription into a Volubilis EASYTHAI transcription."""
    s = s.replace("-", "").replace(" ", "")
    for k, v in ASCIIFY.items():
        s = s.replace(k, v)
    for tone in VOLUBILIS_TONES.keys():
        s = s.replace(tone, "")
    return s

def romanize_from_volubilis(src, thai):
    if not src:
        return None
    
    if src[0] not in VOLUBILIS_TONES.keys():
        src = "-" + src

    src = src.replace("...", " ")
    
    def volubilis_to_aua(m):
        tone_mark = m.group(1)
        syl = m.group(2)
        which_tone = VOLUBILIS_TONES[tone_mark]
        for match, repl in VOLUBILIS_VOWELS.items():
            syl = re.sub(match, repl, syl)
        return add_tone_mark(syl, which_tone) + "&"
        
    result = re.sub(r"([-_\\/¯])\s*([a-zA-ZāīūēōøǿĀĪŪĒŌØǾ]+)",
                    volubilis_to_aua, normalize('NFC', src))
    result = re.sub(r"\.(?!\s|$)", r". ", result)
    # Preserve spaces between words if they were there in the original
    result = result.replace("& ", " ").replace("&-", "-").replace("&.", ".").strip("&")
    result = re.sub(NEEDS_GLOTTAL_STOP, r"\1ˀ", result)
    
    # The Volubilis romanization of diphthongs is ambiguous with regard to glottal stops.
    # Diphthongs with glottal stops are actually rare, so only add them in the few cases that need them
    if thai in SHORT_DIPHTHONG_WORDS:
        result = re.sub(NEEDS_GLOTTAL_STOP_DIPH, r"\1ˀ", result)
    
    result = "•".join([chunk for chunk in result.split("&") if chunk])

    return result


def make_tltk(src):
    if not src:
        return None
    if not re.match(r"[ก-๙]+", src):
        return None  # Ignore non-Thai words
    
    if "โฮล์มส์" in src:
        src = src.replace("โฮล์มส์", "โฮมส์")
    if "นทร์" in src:
        src = src.replace("นทร์", "นท์")
    
    def replace_with_translit(m):
        syl = m.group()
        return transliterate(syl, engine="tltk_g2p")
        
    # PyThaiNLP transliteration only works on contiguous Thai characters
    try:
        src = src.replace("ฅ", "ค") # TLTK can't process this obsolete letter
        result = re.sub(r"[ก-๙]+", replace_with_translit, src)
        if "-0" in result:
            # Syllables ending in H seem to trigger bad output
            print(f"Failed to transliterate {src} into TLTK notation ({e})")
            return None
        return result
    except Exception as e:
        print(f"Failed to transliterate {src} into TLTK notation ({e})")
        return None


def romanize_from_tltk(tltk):
    if not tltk:
        return None
    tltk = tltk.replace("~", "•").replace("'", "•").rstrip("-")
    
    def tltk_to_my_romanization(m):
        syl = m.group(1)
        tone_num = m.group(2)
        for k, v in TLTK_NOTATION.items():
            syl = syl.replace(k, v)
        which_tone = TLTK_TONES[tone_num]
        return add_tone_mark(syl, which_tone)
        
    result = re.sub(r"([a-zOUCH?N@]+)([0-4])", tltk_to_my_romanization, tltk)
    result = re.sub(r"\.(?!\s|$)", r". ", result)
    result = replace_repeater(result)
    result = result.replace("•pai+yaan+nóy", "").replace("pai+yaan+nóy•", "")
    
    # Bug in TLTK does not process NTR cluster properly in Sanskrit/Pali-derived words
    # Note: this fails on "จันทระ" because TLTK doesn't put glottal stops after short vowels
    result = re.sub(r"n•thá•rá(?=\s|$)", "n•thɔɔn", result)
    result = re.sub(r"n•thá•rá(?=•)", "n•thrá", result)

    result = re.sub(NEEDS_GLOTTAL_STOP, r"\1ˀ", result)
    # result = re.sub(NEEDS_GLOTTAL_STOP_DIPH, r"\1ˀ", result)

    result = re.sub(INDIAN_NAMES_DRA, r"\2\1•thráˀ", result)

    if not result or result.startswith("•") or result.endswith("•") or "••" in result:
        return None
    
    return result


def respell(thai):
    def replace_with_respelling(m):
        return pronunciate(m.group(), engine="w2p")
    return re.sub(r"[ก-๙]+", replace_with_respelling, thai)


def paiboon_to_aua(paiboon):
    result = paiboon
    result = re.sub(r"(^|-| )([ptk])", r"\1\2h", result)
    result = re.sub(r"(^|-| )g", r"\1k", result)
    result = re.sub(r"(^|-| )dt", r"\1t", result)
    result = re.sub(r"(^|-| )bp", r"\1p", result)
    result = re.sub(r"(?<![bdfghjklmnprstwyiìíîǐˀ])i(?=-|$)", r"y", result)
    result = re.sub(r"([aàáâǎ])ao", r"\1aw", result)
    result = re.sub(r"([iìíîǐ])ia", r"\1a", result)
    result = re.sub(r"([uùúûǔ])ua", r"\1a", result)
    result = re.sub(r"ʉ([\u0302\u030C\u0300\u0301]?)ʉa", r"ʉ\1a", result)
    result = result.replace("ŋ", "ng")
    result = re.sub(r"(^|-| )(?=[aàáâǎiìíîǐuùúûǔoòóôǒeéèêěʉəɔɛ])", r"\1ˀ", result, flags=re.IGNORECASE)
    result = re.sub(r"-(?!$)", "•", result)

    result = re.sub(NEEDS_GLOTTAL_STOP, r"\1ˀ", result)
    result = result.strip("•")
    return result


def ipa_to_aua(ipa):
    ipa = ipa.replace(" ", "")
    ipa = re.sub(r"(.)ː", r"\1\1", ipa)
    for k, v in IPA_REPLACEMENTS.items():
        ipa = ipa.replace(k, v)
    result = []
    for syl in ipa.split("."):
        # Bad parse, but don't crash
        if not syl:
            continue
        m = re.search(r"(.+?)([˩˨˧˦˥]+)", syl)
        # Catastrophic failure
        if not m:
            return None
        base = m.group(1)
        tone_mark = m.group(2)
        which_tone = IPA_TONES[tone_mark]
        result.append(add_tone_mark(base, which_tone))
    result = "•".join(result)
    result = re.sub(NEEDS_GLOTTAL_STOP, r"\1ˀ", result)
    result = result.strip("•")
    return result

    
SPELLED_OUT = {
    "0": "ศูนย์",
    "1": "หนึ่ง",
    "2": "สอง",
    "3": "สาม",
    "4": "สี่",
    "5": "ห้า",
    "6": "หก",
    "7": "เจ็ด",
    "8": "แปด",
    "9": "เก้า",
    "10": "สิบ",
    "20": "ยี่สิบ",
    "100": "ร้อย",
    "1000": "พัน",
    "+1": "เอ็ด",
    "A": "เอ",
    "B": "บี",
    "C": "ซี",
    "D": "ดี",
    "E": "อี",
    "F": "เอฟ",
    "G": "จี",
    "H": "เอช",
    "I": "ไอ",
    "J": "เจ",
    "K": "เค",
    "L": "แอล",
    "M": "เอ็ม",
    "N": "เอ็น",
    "O": "โอ",
    "P": "พี",
    "Q": "คิว",
    "R": "อาร์",
    "S": "เอส",
    "T": "ที",
    "U": "ยู",
    "V": "วี",
    "W": "ดับเบิลยู",
    "X": "เอ็กซ์",
    "Y": "วาย",
    "Z": "ซี",
    ".": "จุด"
}

def spell_out_alphanum(thai, variants=""):
    
    # Specific headwords
    if thai == "ทรงผม MoHawk":
        return thai
    if "O-NET" in thai:
        return thai
    
    new_thai = thai
    if variants and " = " not in variants and not re.search(r"[A-Za-z๐-๙][A-Z\.๐-๙]*", variants):
        new_thai = variants

    any_alphanum = re.search(r"[0-9A-Za-z][0-9A-Z\.]*", new_thai)
    if not any_alphanum:  # Variant has a spelled-out version
        return new_thai
    
    for alphanum in re.finditer(r"[0-9A-Za-z][0-9A-Z\.]*", new_thai):
    
        alphanum_chars = [char for char in alphanum.group()]
        alphanum_split = "-".join(alphanum_chars)

        alphanum_split = re.sub(r"(?<!\d-)2-(\d)-(\d)-(\d)(?!-\d)", r"2-1000-\1-100-\2-10-\3", alphanum_split)
        alphanum_split = re.sub(r"(?<!\d-)(\d)-0-0(?!-\d)", r"\1-100", alphanum_split)
        alphanum_split = re.sub(r"(?<!\d-)([1-9])-1(?!-?\d)", r"\1-10-+1", alphanum_split)
        alphanum_split = re.sub(r"(?<!\d-)([1-9])-(\d)(?!-?\d)", r"\1-10-\2", alphanum_split)
        alphanum_split = alphanum_split.replace("-0-10", "-")
        alphanum_split = alphanum_split.replace("1-10", "10")
        alphanum_split = alphanum_split.replace("2-10-", "20-")
        alphanum_split = alphanum_split.replace("0-0", "0")

        # Adjustments for specific headwords
        alphanum_split = alphanum_split.replace("1-3-0", "100-3-10")
        alphanum_split = alphanum_split.replace("9-10-6", "9-6")
        alphanum_split = alphanum_split.replace("9-0-4", "9-100-4")
        
        alphanum_chars = alphanum_split.split("-")
        spelled = " ".join([SPELLED_OUT[char.upper()] for char in alphanum_chars])

        new_thai = new_thai.replace(alphanum.group(), spelled)

    return new_thai


def reconstruct_from_syllables(thai, target_num_syllables):
    thai_sylls = []
    for word in re.split(r"\s|-", thai):
        for syl in syllable_tokenize(word):
            if syl in {" ", "-"}:
                continue
            thai_sylls.append(syl)
    from_tltk = [romanize_from_tltk(make_tltk(s)) for s in thai_sylls]
    new_syllables = []
    for syl in from_tltk:
        if not syl:
            continue
        if "•" in syl:
            new_syllables.extend(syl.split("•"))
        else:
            new_syllables.append(syl)

    if len(new_syllables) != target_num_syllables:
        raise Exception(
            f"{thai}: Expected {target_num_syllables} syllables, got {len(new_syllables)}: {new_syllables}")

    result = "•".join(new_syllables).replace("ˀ•", "•")
    result = result.replace("bɔɔ•rí•tìt", "brì•tìt")
    if "ๆ" in result:
        result = re.sub(r"([^•]+)•ๆ", r"\1•\1", result)
    result = re.sub(NEEDS_GLOTTAL_STOP, r"\1ˀ", result)
    result = re.sub(NEEDS_GLOTTAL_STOP_DIPH, r"\1ˀ", result)
    result = result.strip("•")
    return result