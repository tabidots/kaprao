"""
Extract generic words from the English Wikipedia title set by POS-tagging lowercased versions
of the titles. This yields some false positives (like "london") but should generally be OK for
the purpose of narrowing down the unique portions of titles.
"""

from dict.scripts.paths import DB_PATH, RAW_DIR
import sqlite3
from collections import Counter
from flair.models import SequenceTagger
from flair.data import Sentence
from tqdm import tqdm

GENERIC_POS = {'CC', 'CD', 'DT', 'EX', 'IN', 'JJ',
               'JJR', 'JJS', 'MD', 'NN', 'NNS', 'PDT', 'TO'}

def get_generic_words():
    tagger = SequenceTagger.load('flair/pos-english-fast')
    generics = Counter()

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # Get total count
        c.execute("SELECT COUNT(*) FROM th_wikipedia WHERE english IS NOT NULL")
        total_count = c.fetchone()[0]

        # Process in larger batches
        batch_size = 2000  # Increased from 500
        offset = 0

        with tqdm(total=total_count, desc="Processing titles") as pbar:
            while offset < total_count:
                # Get batch of text only
                c.execute("""
                    SELECT english 
                    FROM th_wikipedia 
                    WHERE english IS NOT NULL 
                    LIMIT ? OFFSET ?
                """, (batch_size, offset))

                rows = c.fetchall()
                if not rows:
                    break

                # Filter and create sentences more efficiently
                texts = [row[0].strip().lower()
                         for row in rows if row[0] and row[0].strip()]

                if texts:
                    # Create sentences in batch
                    sentences = [Sentence(text) for text in texts]

                    # Predict in batch with larger mini_batch_size
                    tagger.predict(sentences, mini_batch_size=256)  # Increased

                    # Process all sentences efficiently
                    for sentence in sentences:
                        for token in sentence:
                            pos_tag = token.get_label('pos').value
                            word = token.text
                            if pos_tag in GENERIC_POS and word.isalpha():
                                generics[word.lower()] += 1

                offset += batch_size
                pbar.update(len(rows))

    return generics


if __name__ == "__main__":
    generics = get_generic_words()

    with open(RAW_DIR / "generic_english.txt", "w") as f:
        for word, count in generics.most_common():
            if count <= 5:
                break
            f.write(f"{word}\t{count}\n")