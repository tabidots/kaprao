from dict.scripts.paths import RAW_DIR
from dict.scripts.utils import INDEPENDENT_VOWELS, DIACRITICS
import csv
import re

CONS_MAPPING = {    
    "ก": {"k", "g", "c", "q"},
    "ข": {"k"},
    "ค": {"k", "g", "kh", "c", "q", "j", "hk", "ha", "he", "xanthos"},
    "คว": {"qu", "sk", "kj", "hu", "ku", "kw", "kou", "gw", "ju", "khw", "khow", 
           "kow", "qw", "hv", "kev", "kav", "cav", "gav", "cuo", "qantas"},
    "ฆ": {"kh", "j", "gh", "h", "k", "ge", "gi", "x"},
    "ง": {"ng", "ny", "hong"},
    "จ": {"j", "ch", "c", "g", "ge", "gi", "gy", "dj", "tr", "ky", "zh", "z", 
          "dz", "dž", "ď", "ġ", "đ", "gj", "de ", "di", "xh", "tj", "ts"},
    "ฉ": {"ch", "she", "shi", "qi", "qu", "c"},
    
    "ช": {"rz", "j", "ge", "gi", "gy", "dj", "sh", "ch", "st", "sp", "sch", 
          "c", "ç", "ć", "č", "cz", "š", "sz", "ś", "sj", "ts", "x", "zh", 
          "ş", "ș", "tch", "ž", "ż", "q", "sci", "sce", "z", "si", "ṣ",
          "sean", "sya", "thi", "séamus"},
    # This letter is also used for Hungarian "s" and Norwegian "ki" (both pronounced "sh")
    # but adding those here will cause a lot of false positives

    "ซ": {"s", "š", "c", "ç", "z", "ž", "ẓ", "dh", "gia", "dươ", "duy", 
          "þ", "tz", "ts", "dz", "ps", "x", "hs", "6"},
    "ฌ": {"j", "ge", "gé", "gi", "gy", "nh", "dj", "zh", "ž", "zs", "ch", "sean", "shawn", "shaun"},
    "ญ": {"y", "j", "ny", "nh", "gi", "ge", "dj", "ni", "ne", "hn", "hyapha"},
    "ฎ": {"d",  "z", "ḍ"},
    "ฏ": {"t"},
    "ฐ": {"t", "th", "dh"},
    "ฑ": {"t", "ḍ"},
    "ณ": {"n"},
    "ด": {"d", "the", "that", "đ", "wplace"},
    "ต": {"t", "d", "cz"},
    "ถ": {"th", "t"},
    "ท": {"t", "ht", "d", "pt", "ct", "2"},
    "ทร": {"t", "d", "s"},
    "ธ": {"t", "th", "d", "dh"},
    "น": {"n", "kn", "dn", "mn", "hn", "gn", "pn", "cn"},
    "บ": {"b", "p", "v", "gb"},
    "ป": {"p", "b"},
    "ผ": {"p"},
    "ฝ": {"f", "ph"},
    "พ": {"p", "b", "hp"},
    "ฟ": {"f", "ph", "v", "pf", "4", "5", "15"},
    "ภ": {"bh", "p"},
    "ม": {"m", "bau", "m", "nm", "μ", "hem", "heym", "hom"},
    "ย": {"y", "hj", "lj", "ll", "j", "eu", "iu", "io", "ia", "u", 
          "gj", "gä", "gö", "gy", "ge", "gi", "e", "hoy"},
    "ร": {"r", "wr", "har", "han", "her"},
    "ฤ": {"r", "hr", "li"},
    "ล": {"l", "hol", "hal"},
    "ว": {"w", "v", "ł", "o", "jo", "hv", "hu", "rw", "uíge", "hou"},
    "ศ": {"s", "sh", "ce", "ci", "z", "ś"},
    "ษ": {"th", "dh", "ṯ"},
    "ส": {"s", "z", "ce", "ci", "cy", "ts", "xi", "xu", "ś", "hs", "ps", 
          "dục", "thaton", "doãn", "xã", "takayutpi"},
    "ห": {"h"},
    "ฮ": {"h", "kh", "j", "r", "gi", "ge", "x", "ħ", "who"},
}

VOWEL_MAPPING = {
    "เอา": {"ao", "au", "ou"},
    "อาว": {"ou", "aw", "ao", "áo", "av", "áv", "arw"}, # Can be diphthong or V+C
    "เอะ": {"e"},    
    "เออ": {"oe", "eu", "ue", "er", "e", "ö", "he", "ir", "ur", "ø", "ơ", "aar"},
    "เอีย": {"ia", "ie", "ea", "ye", "yê"},
    "เอือ": {"uea", "ua", "eua"},
    "เอิ": {"ö", "eö", "he", "â", "oe", "ear", "er"},
    "เอ": {"e", "ay", "ei", "a", "é", "he", "hé", "x", "oe", "æ"},
    "แอ": {"ae", "a", "ä", "æ", "é", "e", "he", "in"},
    "โอ": {"o", "oh", "ou", "au", "ō", "hau", "aa", "å", "ho", "ó", "eoin"},
    "ไอ": {"ai", "ay", "i", "ei", "ey", "ej", "ae"},
    "ใอ": {"ai", "ay"}, # Not likely to occur anyway
    "อัว": {"ua", "oua", "ogre"},
    "อำ": {"am", "um", "om"},
    "อะ": {"a", "ha"},
    "อั": {"a", "ha", "á", "un", "umb", "up", "ul", "en", "es", "ush", "ān",
           "usni", "erbil"},
    "อา": {"a", "ah", "ar", "á", "ā", "ha", "er"},
    "อิ": {"i", "e", "hi", "ae", "yng", "ytt", "yrausquin"},
    "อี": {"i", "e", "hi", "î", "ae", "oe", "y ", "yv", "yp", "hymne", "yannick"},
    "อึ": {"u", "eu", "ue", "ư",  "ü", "ŭ", "es", "yggdrasil",
           "ng", "nk", "nz", "nd", "mw", "ms", "mb", "mp", "mn", "mv", "mk"},
    "อือ": {"u", "y", "ü"},
    "อื": {"u", "eu", "ue", "ư"},
    "อุ": {"u", "oo", "ou", "o", "woo", "wu", "wú", "hu", "hou"},
    "อู": {"u", "oo", "ou", "o", "woo", "wu", "wú", "hu", "hou"},
}

SONORANTS = "วมนลงยรญ"


def is_plausible_translit(thai, roman):
    thai_without_prevowel = thai[1:] if thai[0] in INDEPENDENT_VOWELS else thai
    if thai_without_prevowel.startswith("ทร"):
        first_thai = "ทร"
    elif thai_without_prevowel.startswith("คว"):
        first_thai = "คว"
    elif thai_without_prevowel.startswith("อย") and thai_without_prevowel == thai:
        # Prevowel + อย = V+C, otherwise vowel o + consonant y
        first_thai = "ย"
    elif any(thai_without_prevowel.startswith("ห" + sonorant) for sonorant in SONORANTS):
        first_thai = thai_without_prevowel[1]
    else:
        first_thai = thai_without_prevowel[0]

    if re.fullmatch(r"[A-Z\.0-9\-]+", roman):
        return True
    if "(" in roman:
        return True

    norm_roman = re.sub(r"[Ꞌʽʿ'ʻʾ\.]", "", roman).lower()

    if first_thai == "อ":
        plain_thai = "".join(
            [char for char in thai if char not in DIACRITICS])
        for vowel, initial_romans in VOWEL_MAPPING.items():
            if vowel == "เอ" and re.match(r"[A-Z][A-Z-']", roman):
                continue
            if plain_thai.startswith(("เออา", "เอออ")):
                if vowel == "เออ":
                    continue
                if vowel == "เอ" and re.match(r"[A-Z][A-Z-']", roman):
                    continue
                if vowel == "เอ" and not norm_roman.startswith(tuple(initial_romans)):
                    return False
            if plain_thai.startswith(vowel):
                if not norm_roman.startswith(tuple(initial_romans)):
                    return False
                break
    elif initial_romans := CONS_MAPPING.get(first_thai, None):
        if not norm_roman.startswith(tuple(initial_romans)):
            return False
    
    return True


def validate_all():

    with open(RAW_DIR / "transliterations.tsv", "r") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)
        for row in reader:
            thai, roman = row

            if roman.endswith("†"):
                # This symbol marks a known incorrect transliteration
                # That is, the Thai is valid and it is intended to correspond to the
                # Latin string, but is not correct according to the source language pronunciation
                continue

            if not is_plausible_translit(thai, roman):
                print(f"{thai}\t{roman}")


if __name__ == "__main__":
    validate_all()
