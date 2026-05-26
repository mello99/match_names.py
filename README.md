# match_names.py
A standalone Python script for reconciling name entities against a local copy of the Library of Congress Name Authority File (LCNAF) without requiring a network connection or external services. 

The script reads a CSV file containing name data, queries a local SQLite database built from one or more MARC21 (.mrc) authority files, and returns ranked match candidates for each name using fuzzy string matching. Results are written to a CSV file that can be reviewed manually or imported into OpenRefine.
