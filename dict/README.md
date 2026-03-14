# Kaprao dictionary scripts

This directory contains data ingestion, cleanup, and validation scripts for the Kaprao Thai Reading Assistant.

Pipeline:

(Remember to run all files of the form `a/b/c.py` as `python -m a.b.c`)

## I. Wiktionary

- Trim Kaikki dump of Thai-language edition of Wiktionary (thwiki):

```bash
gunzip -c dict/raw/raw-wiktextract-data.jsonl.gz | jq -c 'select(.lang_code == "th" and (.word | test("^[ก-๙]+")))' > dict/raw/kaikki-thwiktionary-filtered.jsonl
```

- Also make sure you have `dict/raw/kaikki.org-dictionary-Thai.jsonl`, the Kaikki dump of the Thai headwords in the English-language edition of Wiktionary (enwiki).

- Run `dict/scripts/import_wiktionary.py`. These pronunciations will be a source of truth in the next step.

## II. Volubilis dataset (base dictionary)

- Start with the raw Volubilis CSV (`dict/raw/VOLUBILIS Mundo(Volubilis).csv`)
- Import into SQLite using `dict/scripts/import_volubilis.py`

## III. Add phonetic annotations

- Run `dict/scripts/add_phonetic.py`.

## IV. Fill in "see also" data

- Run `dict/scripts/see_also.py`.

## V. Fill in English definitions

- The Volubilis dataset has about 8k rows with only French definitions and no English definitions. Use MarianMT to translate these from a CSV (`dict/raw/french-defs.tsv` -> `dict/raw/french-translations.tsv`)
- Run `dict/scripts/add_english.py` to write these to the DB.

## VI. Dealing with OOV words (very important!)

### Thai Wikipedia article titles and parallel (English) titles

- Download `thwiki...langlinks.sql.gz` and `thwiki...pages-articles.xml.bz2`
- Download `enwiki...page.sql.gz`, `enwiki...categorylinks.sql.gz`, and `enwiki...linktarget.sql.gz`
- Run `dict/scripts/wikipedia_dumps_to_tsv.py` to create some intermediate TSVs. This will save time if you need to repeat the next step (mostly to refine the `clean_title()` function), because it's pretty heavy parsing (for Thai + English it takes ~7.5 minutes)
- Import into SQLite using `dict/scripts/import_wikipedia.py`
- The resulting table has the Thai title, English parallel title where available, as well as all of the English categories that the English title belongs to

## IV. Export

Run `./build/build-dict.sh` to run the export script and gzip the dictionary file for use in the browser extension.
