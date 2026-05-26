# match_names.py
# Written with Claude Sonnet 4.6

import sqlite3
import csv
import re
from rapidfuzz import fuzz

DB_FILE      = "C:\Path\To\lcnaf.db"       # path to your SQLite database
INPUT_CSV    = "C:\Path\To\input_spreadsheet_names.csv"      # your input CSV file
OUTPUT_CSV   = "C:\Path\To\reconciled.csv" # output file with match results added
NAME_COLUMN  = "[insert name column from spreadsheet]"           # name of the column containing names to match
MATCH_LIMIT  = 3                # how many candidates to return per name
MIN_SCORE    = 50               # minimum score to include a match (0-100)

def clean_query(query):
    """Strip MARC subfield notation and URIs from a name string."""
    match = re.search(r'\$a([^$]+)', query)
    if match:
        query = match.group(1)
    query = re.sub(r'\$[a-z0-9]+\S*', '', query)
    query = re.sub(r'https?://\S+', '', query)
    query = query.strip().rstrip(',')
    return query

def search(c, query, limit=3):
    """Search the database for a name and return scored candidates."""
    query = clean_query(query)
    if not query:
        return []

    safe_query = '"' + query.replace('"', '""') + '"'

    try:
        c.execute("""
            SELECT n.id, n.label, n.variants
            FROM names_fts f
            JOIN names n ON n.rowid = f.rowid
            WHERE names_fts MATCH ?
            LIMIT 50
        """, (safe_query,))
        rows = c.fetchall()
    except sqlite3.OperationalError:
        c.execute("""
            SELECT id, label, variants
            FROM names
            WHERE label LIKE ?
            LIMIT 50
        """, (f"%{query}%",))
        rows = c.fetchall()

    if not rows:
        return []

    scored = []
    for lccn, label, variants in rows:
        score = fuzz.token_sort_ratio(query.lower(), label.lower())
        for v in (variants or "").split("|"):
            if v:
                s = fuzz.token_sort_ratio(query.lower(), v.lower())
                score = max(score, s)
        scored.append((lccn, label, score))

    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:limit]

def main():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    with open(INPUT_CSV, newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        original_fields = reader.fieldnames

        # Build output column names — one set per candidate rank
        extra_fields = []
        for i in range(1, MATCH_LIMIT + 1):
            extra_fields += [
                f"match_{i}_name",
                f"match_{i}_id",
                f"match_{i}_score",
            ]

        out_fields = original_fields + extra_fields

        rows_out = []
        total = 0
        matched = 0

        for row in reader:
            query = row.get(NAME_COLUMN, "").strip()
            candidates = search(c, query, MATCH_LIMIT) if query else []

            # Filter by minimum score
            candidates = [(lccn, label, score)
                          for lccn, label, score in candidates
                          if score >= MIN_SCORE]

            for i in range(1, MATCH_LIMIT + 1):
                if i <= len(candidates):
                    lccn, label, score = candidates[i - 1]
                    row[f"match_{i}_name"]  = label
                    row[f"match_{i}_id"]    = lccn
                    row[f"match_{i}_score"] = score
                else:
                    row[f"match_{i}_name"]  = ""
                    row[f"match_{i}_id"]    = ""
                    row[f"match_{i}_score"] = ""

            if candidates:
                matched += 1
            total += 1

            rows_out.append(row)

            if total % 100 == 0:
                print(f"  Processed {total:,} rows...")

    conn.close()

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"\nDone.")
    print(f"  Total rows processed : {total:,}")
    print(f"  Rows with a match    : {matched:,}")
    print(f"  Rows with no match   : {total - matched:,}")
    print(f"  Output saved to      : {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
