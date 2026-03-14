from dict.scripts.paths import DB_PATH
from dict.scripts.lexicon import Lexicon
import sqlite3
from collections import Counter
import argparse
import re

max_ttc = 63126
max_wiki = 4733


def mark_head_nouns():
    lexicon = Lexicon(nouns_only=True)
    head_nouns = Counter()
    batch = []

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE th_wikipedia SET head_noun = NULL")

        c.execute("SELECT id, thai FROM th_wikipedia")

        for (id, thai) in c.fetchall():
            if prefixes := lexicon.get_prefix_words(thai, include_translit=True):
                if longest := max(prefixes, key=len):
                    if thai.startswith("พระยา") and longest == "พระ":
                        continue
                    if thai.startswith("วิทยาลัยเทคโนโลย") and longest == "วิทยาลัยเทค":
                        longest = "วิทยาลัยเทคโนโลยี"
                    if longest == "วงศ์นก":
                        longest = "วงศ์"
                    if longest == "จักรพรรดินี" and thai.startswith("จักรพรรดินีโคไล"):
                        longest = "จักรพรรดิ"
                    head_nouns[longest] += 1
                    batch.append((longest, id))

            if len(batch) >= 10_000:
                c.executemany("""
                    UPDATE th_wikipedia
                    SET head_noun = ?
                    WHERE id = ?
                """, batch)
                conn.commit()
                batch = []

        if batch:
            c.executemany("""
                UPDATE th_wikipedia
                SET head_noun = ?
                WHERE id = ?
            """, batch)
            conn.commit()

    c.execute("DROP TABLE IF EXISTS wiki_head_nouns")
    c.execute("""
        CREATE TABLE wiki_head_nouns (
            word TEXT PRIMARY KEY,
            title_coverage integer,
            normalized_ttc REAL
        )
    """)

    data = [
        (word, count, lexicon.base.get(word, 0) / max_ttc * 100)
        for word, count in head_nouns.items()
        if count > 15
    ]

    c.executemany("""
        INSERT INTO wiki_head_nouns (word, title_coverage, normalized_ttc)
        VALUES (?, ?, ?)
    """, data)
    print(f"{len(data)} head nouns added to head nouns table.")
    conn.commit()

    # Delete head noun in th_wikipedia where it doesn't exist in wiki_head_nouns
    c.execute("""
        UPDATE th_wikipedia AS w
        SET head_noun = NULL
        WHERE w.head_noun IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM wiki_head_nouns h 
            WHERE h.word = w.head_noun
        )
    """)

    conn.commit()


def segment_titles(incremental_update=False):
    """
    Segment all Wikipedia titles and mark coverage status.
    
    Args:
        incremental_update: If True, only re-segment titles that might have changed
                          due to newly added lexicon entries. If False, re-segment everything.
    """
    lexicon = Lexicon()

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        def _segment_and_update(titles):
            """
            Segment a list of titles and update database with results.
            
            Args:
                titles: List of (id, thai, head_noun) tuples
            
            Returns:
                Set of newly covered words (for incremental updates)
            """
            fully_covered_ids = []
            segmentations = []
            newly_covered_words = set()

            for id, thai, head_noun in titles:
                # Try segmenting with head noun first
                text_to_segment = thai
                mask, words = lexicon.coverage_mask(
                    thai, include_translit=True)
                
                # If head noun exists but wasn't matched at position 0, strip it
                first_segment = next((w for w, s, _ in words if s == 0), None)
                prefix = ""
                if not head_noun:
                    pass
                elif thai in lexicon.safe_titles:
                    pass
                elif not first_segment or len(head_noun) > len(first_segment):
                    text_to_segment = thai[len(head_noun):]
                    prefix = head_noun
                elif len(head_noun) < len(first_segment):
                    text_to_segment = thai[len(first_segment):]
                    prefix = first_segment

                if prefix:
                    mask, words = lexicon.coverage_mask(
                        text_to_segment, include_translit=True)

                # Generate segmentation string
                segmentation_str = lexicon.coverage_to_string(
                    text_to_segment, words, mask)

                # Prepend head noun if we stripped it
                if prefix:
                    segmentation_str = f"[{prefix}]{segmentation_str}"

                # Check if fully covered (no OOV chunks)
                is_fully_covered = "<" not in segmentation_str or thai in lexicon.safe_titles
                
                # NOTE: Now that the bulk of the OOV mining is done, 
                # just write the segmentation to the DB for all titles
                # This makes it easier to filter entries for export
                is_fully_covered = True

                if is_fully_covered:
                    fully_covered_ids.append(id)
                    # Track newly covered words for propagation
                    newly_covered_words.update(
                        re.findall(r"\[([^\]<>]+?)\]", segmentation_str)
                    )
                else:
                    segmentations.append((segmentation_str, id))

            # Batch update fully covered titles
            if fully_covered_ids:
                c.executemany(
                    "UPDATE th_wikipedia SET has_oov = 0, segmentation = NULL, longest_oov = NULL WHERE id = ?",
                    [(id,) for id in fully_covered_ids]
                )

            # Batch update partial coverage titles
            if segmentations:
                c.executemany(
                    "UPDATE th_wikipedia SET has_oov = 1, segmentation = ?, longest_oov = NULL WHERE id = ?",
                    segmentations
                )

            conn.commit()
            return newly_covered_words

        # Main execution logic
        if incremental_update:
            # Step 1: Re-segment titles that were manually marked as covered
            #
            # Workflow: When manually adding transliterations to the TSV, we update
            # has_oov=0 in SQLite Studio but leave segmentation non-NULL (too tedious
            # to update by hand). This creates a "dirty bit" pattern:
            #   - has_oov=0 + segmentation=NULL → cleanly covered
            #   - has_oov=0 + segmentation!=NULL → manually marked, needs re-segmentation
            #
            # The cleanup step at the end ensures all truly covered titles have NULL segmentation.
            c.execute("""
                SELECT id, thai, head_noun 
                FROM th_wikipedia
                WHERE segmentation IS NOT NULL AND has_oov = 0
            """)
            manually_marked = c.fetchall()

            if manually_marked:
                print(
                    f"Re-segmenting {len(manually_marked)} manually marked titles...")
                newly_covered_words = _segment_and_update(manually_marked)

                # Step 2: Propagate to titles containing newly covered words
                # (they might now be fully covered too)
                if newly_covered_words:
                    print(
                        f"Found {len(newly_covered_words)} newly covered words, propagating...")

                    # Use temp table for efficient lookup
                    c.execute(
                        "CREATE TEMP TABLE tmp_new_words (word TEXT PRIMARY KEY)")
                    c.executemany(
                        "INSERT INTO tmp_new_words (word) VALUES (?)",
                        [(w,) for w in newly_covered_words]
                    )

                    c.execute("""
                        SELECT DISTINCT t.id, t.thai, t.head_noun
                        FROM th_wikipedia t
                        WHERE t.has_oov = 1
                          AND EXISTS (
                            SELECT 1 FROM tmp_new_words w
                            WHERE t.thai LIKE '%' || w.word || '%'
                          )
                    """)
                    affected_titles = c.fetchall()

                    if affected_titles:
                        print(
                            f"Re-segmenting {len(affected_titles)} affected titles...")
                        _segment_and_update(affected_titles)
            else:
                print("No manually marked titles to process.")
        else:
            # Full re-segmentation: process all titles from scratch
            print("Full re-segmentation of all titles...")
            c.execute("SELECT id, thai, head_noun FROM th_wikipedia")
            all_titles = c.fetchall()
            _segment_and_update(all_titles)

        # Print statistics
        c.execute("SELECT COUNT(*) FROM th_wikipedia WHERE has_oov = 0")
        fully_covered = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM th_wikipedia")
        total = c.fetchone()[0]

        print(f"\n{'='*60}")
        print(f"Coverage Statistics:")
        print(f"{'='*60}")
        print(
            f"Fully covered: {fully_covered:,} / {total:,} ({100 * fully_covered / total:.2f}%)")

        c.execute("""
            SELECT COUNT(*) FROM th_wikipedia
            WHERE has_oov = 0 AND english IS NOT NULL
        """)
        covered_with_english = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM th_wikipedia WHERE english IS NOT NULL")
        total_with_english = c.fetchone()[0]

        print(f"With parallel English titles: {covered_with_english:,} / {total_with_english:,} "
              f"({100 * covered_with_english / total_with_english:.2f}%)")
        print(f"{'='*60}\n")


def patch():
    print("Patching...")

    lexicon = Lexicon()

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, thai FROM th_wikipedia
            WHERE (thai like '%มหา%' or segmentation like '%[มหา]%')
            AND english like '%Maha%'
        """)

        batch = []
        titles = c.fetchall()
        for id, thai in titles:
            text_to_segment = thai
            mask, words = lexicon.coverage_mask(
                    thai, include_translit=True)

            segmentation_str = lexicon.coverage_to_string(
                text_to_segment, words, mask)

            batch.append((segmentation_str, id))

        c.executemany(
            "UPDATE th_wikipedia SET segmentation = ? WHERE id = ?",
            batch
        )

        conn.commit()


def fill_longest_oov():
    print("Filling longest OOV chunks...")

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, segmentation FROM th_wikipedia
            WHERE has_oov = 1 AND segmentation IS NOT NULL
        """)

        batch = []
        titles = c.fetchall()
        for id, segmentation in titles:
            longest_oov = None
            for chunk in re.findall(r"<([^>]+)>", segmentation):
                if not longest_oov or len(chunk) > len(longest_oov):
                    longest_oov = chunk
            batch.append((longest_oov, id))

            if len(batch) >= 1_000:
                c.executemany(
                    "UPDATE th_wikipedia SET longest_oov = ? WHERE id = ?",
                    batch
                )
                conn.commit()
                batch = []
        
        if batch:
            c.executemany(
                "UPDATE th_wikipedia SET longest_oov = ? WHERE id = ?",
                batch
            )
            conn.commit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Segment Thai Wikipedia titles and compute lexicon coverage"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only re-segment titles that were manually marked as covered (faster)"
    )
    args = parser.parse_args()

    if not args.incremental:
        mark_head_nouns()

    segment_titles(incremental_update=args.incremental)
    