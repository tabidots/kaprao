import gzip
import re
from dict.scripts.paths import RAW_DIR
from collections import defaultdict

SRC_DUMP_DATE = "20260101"
EN_DUMP_DATE = "20260101"
SRC_LANG = "th"

# Step 0: Parse English redirects (needed for resolving page IDs later)
print("=" * 60)
print("STEP 0: Parsing English redirects")
print("=" * 60)

EN_REDIRECT_PATH = RAW_DIR / f"enwiki-{EN_DUMP_DATE}-redirect.sql"

insert_pattern = re.compile(r"INSERT INTO `redirect` VALUES \((.+)\);")
en_redirects = {}

with open(EN_REDIRECT_PATH, 'rt', encoding='utf-8', errors='replace') as f:
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

            en_redirects[page_id] = target_title

print(f"Loaded {len(en_redirects)} English redirects")

# Helper function to resolve redirect chains


def resolve_en_redirect(page_id, title, en_redirects, title_to_page_id):
    """Resolve a redirect chain, return final (page_id, title)"""
    visited = {page_id}
    current_title = title

    # Follow redirect chain
    while page_id in en_redirects:
        target_title = en_redirects[page_id]

        # Look up the target's page_id
        if target_title not in title_to_page_id:
            # Dead redirect, keep current
            break

        page_id = title_to_page_id[target_title]

        # Prevent infinite loops
        if page_id in visited:
            break
        visited.add(page_id)

        current_title = target_title

    return page_id, current_title


# Step 1: Parse langlinks to get source language -> English title mappings
print("\n" + "=" * 60)
print("STEP 1: Parsing langlinks")
print("=" * 60)

LANGLINKS_PATH = RAW_DIR / f"{SRC_LANG}wiki-{SRC_DUMP_DATE}-langlinks.sql.gz"
LANGLINKS_OUTPUT_PATH = RAW_DIR / f"{SRC_LANG}wiki-{SRC_DUMP_DATE}-langlinks.tsv"

insert_pattern = re.compile(r"INSERT INTO `langlinks` VALUES \((.+)\);")
data = []

with gzip.open(LANGLINKS_PATH, 'rt', encoding='utf-8', errors='replace') as f:
    for line in f:
        match = insert_pattern.search(line)
        if not match:
            continue

        values_str = match.group(1)
        rows = values_str.split('),(')

        for row in rows:
            # langlinks structure: (ll_from/page_id, ll_lang, ll_title)
            m = re.search(r'^(\d+),\'(\w+)\',\'(.+?)\'$', row)
            if not m:
                continue

            page_id = m.group(1)
            lang = m.group(2)

            # Only keep English links
            if lang != 'en':
                continue

            title = m.group(3)
            if title[0] + title[-1] == '""':
                title = title[1:-1]
            # Unescape SQL escapes
            title = title.replace('\\\\', '\\').replace(
                '\\"', '"').replace("\\'", "'")

            data.append((page_id, title))

with open(LANGLINKS_OUTPUT_PATH, 'wt', encoding='utf-8') as outf:
    for row in data:
        outf.write('\t'.join(str(x) for x in row) + '\n')

print(f"Wrote {len(data)} langlinks to {LANGLINKS_OUTPUT_PATH.name}")

# Get the needed English titles for next step
needed_en_titles = set(title for _, title in data)

# Step 2: Parse English page.sql to get title -> page_id mappings (only for needed titles)
# We need TWO passes: first to build title_to_page_id map, then to resolve redirects
print("\n" + "=" * 60)
print("STEP 2: Parsing English page IDs")
print("=" * 60)

PAGE_PATH = RAW_DIR / f"enwiki-{EN_DUMP_DATE}-page.sql.gz"
PAGE_OUTPUT_PATH = RAW_DIR / f"enwiki-{EN_DUMP_DATE}-pageids.tsv"

insert_pattern = re.compile(r"INSERT INTO `page` VALUES \((.+)\);")

# First pass: Build complete title -> page_id map (for redirect resolution)
print("  First pass: building title->page_id map...")
title_to_page_id = {}

with gzip.open(PAGE_PATH, 'rt', encoding='utf-8', errors='replace') as f:
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

            title_to_page_id[title] = page_id

print(f"  Built map with {len(title_to_page_id)} titles")

# Second pass: Resolve redirects for needed titles
print("  Second pass: resolving redirects for needed titles...")
data = []

for title in needed_en_titles:
    if title not in title_to_page_id:
        continue

    page_id = title_to_page_id[title]

    # Resolve if it's a redirect
    final_page_id, final_title = resolve_en_redirect(page_id, title, en_redirects, title_to_page_id)

    # Store with ORIGINAL title (from langlinks) but RESOLVED page_id
    data.append((title, final_page_id))

with open(PAGE_OUTPUT_PATH, 'wt', encoding='utf-8') as outf:
    for row in data:
        outf.write('\t'.join(str(x) for x in row) + '\n')

print(f"Wrote {len(data)} page IDs to {PAGE_OUTPUT_PATH.name}")

# Get the needed page IDs for next step (use resolved page IDs)
needed_page_ids = set(int(page_id) for _, page_id in data)

# Step 3: Parse categorylinks (same as before)
print("\n" + "=" * 60)
print("STEP 3: Parsing category links")
print("=" * 60)

CATEGORY_LINKS_PATH = RAW_DIR / f"enwiki-{EN_DUMP_DATE}-categorylinks.sql.gz"
CATEGORY_LINKS_OUTPUT_PATH = RAW_DIR / f"enwiki-{EN_DUMP_DATE}-categorylinks.tsv"

insert_pattern = re.compile(
    r"INSERT INTO `categorylinks` VALUES \((.+)\);", re.DOTALL)
data = []
all_cat_ids = set()
line_count = 0

with gzip.open(CATEGORY_LINKS_PATH, 'rt', encoding='utf-8', errors='replace') as f:
    for line in f:
        line_count += 1

        if line_count % 100000 == 0:
            print(
                f"  Processed {line_count:,} lines, found {len(data):,} page-category links...")

        match = insert_pattern.search(line)
        if not match:
            continue

        values_str = match.group(1)
        rows = values_str.split('),(')

        for row in rows:
            # categorylinks structure: (page_id, ..., category_id)
            m = re.search(r'^(\d+),.+,(\d+)$', row)
            if not m:
                continue

            page_id = int(m.group(1))
            cat_id = int(m.group(2))

            # Only keep links for pages we care about
            if page_id not in needed_page_ids:
                continue

            data.append((page_id, cat_id))
            all_cat_ids.add(cat_id)

# Group by page_id
page_to_cats = defaultdict(list)
for page_id, cat_id in data:
    page_to_cats[page_id].append(cat_id)

with open(CATEGORY_LINKS_OUTPUT_PATH, 'wt', encoding='utf-8') as outf:
    for page_id, cat_ids in page_to_cats.items():
        outf.write(f"{page_id}\t{','.join(map(str, cat_ids))}\n")

print(f"Wrote {len(page_to_cats)} page-category mappings to {CATEGORY_LINKS_OUTPUT_PATH.name}")
print(f"Found {len(all_cat_ids)} unique category IDs")

# Step 4: Parse linktarget (same as before)
print("\n" + "=" * 60)
print("STEP 4: Parsing category names")
print("=" * 60)

CATEGORY_NAMES_PATH = RAW_DIR / f"enwiki-{EN_DUMP_DATE}-linktarget.sql.gz"
CATEGORY_NAMES_OUTPUT_PATH = RAW_DIR / f"enwiki-{EN_DUMP_DATE}-linktarget.tsv"

insert_pattern = re.compile(
    r"INSERT INTO `linktarget` VALUES \((.+)\);", re.DOTALL)
data = []
line_count = 0

with gzip.open(CATEGORY_NAMES_PATH, 'rt', encoding='utf-8', errors='replace') as f:
    for line in f:
        line_count += 1

        if line_count % 10000 == 0:
            print(
                f"  Processed {line_count:,} lines, found {len(data):,} categories...")

        match = insert_pattern.search(line)
        if not match:
            continue

        values_str = match.group(1)
        rows = values_str.split('),(')

        for row in rows:
            # linktarget structure: (link_id, namespace, title)
            m = re.search(r'^(\d+),(\d+),\'(.+)\'$', row)
            if not m:
                continue

            cat_id = int(m.group(1))
            namespace = m.group(2)

            # Only process namespace 14 (categories)
            if namespace != '14':
                continue

            # Only keep categories we need
            if cat_id not in all_cat_ids:
                continue

            title = m.group(3)
            if title[0] + title[-1] == '""':
                title = title[1:-1]
            # Unescape and normalize
            title = title.replace('\\\\', '\\').replace(
                '\\"', '"').replace("\\'", "'").replace('_', ' ')

            data.append((cat_id, title))

            # Early exit if we found all needed categories
            if len(data) == len(all_cat_ids):
                print(
                    f"  Found all {len(data)} needed categories, stopping early")
                break
        else:
            continue
        break

with open(CATEGORY_NAMES_OUTPUT_PATH, 'wt', encoding='utf-8') as outf:
    for row in data:
        outf.write('\t'.join(str(x) for x in row) + '\n')

print(f"Wrote {len(data)} category names to {CATEGORY_NAMES_OUTPUT_PATH.name}")

print("\n" + "=" * 60)
print("DONE! All TSV files generated.")
print("=" * 60)