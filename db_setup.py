import sqlite3

conn = sqlite3.connect('lt_osf.sqlite')

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS users
           (id TEXT PRIMARY KEY,
           full_name TEXT,
           date_created TEXT);
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS jobs
           (id TEXT,
           title TEXT,
           institution TEXT,
           start_year INT,
           end_year INT,
           ongoing INT);
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS education
           (id TEXT,
           degree TEXT,
           institution TEXT,
           start_year INT,
           end_year INT,
           ongoing INT);
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS socials
           (id TEXT,
           platform TEXT,
           name TEXT);
    """
)

conn.commit()
conn.close()

