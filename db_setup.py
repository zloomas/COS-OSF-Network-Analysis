import sqlite3
from config import db_name

conn = sqlite3.connect(db_name)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS users(
           id TEXT PRIMARY KEY,
           full_name TEXT NOT NULL,
           date_created TEXT NOT NULL
           );
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS cos_staff(
           id TEXT PRIMARY KEY,
           current INT NOT NULL DEFAULT 1
           );
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS jobs(
           id TEXT NOT NULL,
           title TEXT NOT NULL,
           institution TEXT NOT NULL,
           start_year INT,
           end_year INT,
           ongoing INT NOT NULL,
           UNIQUE(id, title, institution)
           );
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS education(
           id TEXT NOT NULL,
           degree TEXT NOT NULL,
           institution TEXT NOT NULL,
           start_year INT,
           end_year INT,
           ongoing INT,
           UNIQUE(id, degree, institution)
           );
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS socials(
           id TEXT,
           platform TEXT,
           name TEXT,
           UNIQUE(id, platform, name)
           );
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS nodes(
           id TEXT PRIMARY KEY,
           title TEXT,
           date_created TEXT
           );
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS node_tags(
           id TEXT,
           tag TEXT,
           UNIQUE(id, tag)
           );
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS node_relations(
           parent TEXT,
           child TEXT,
           UNIQUE(parent, child)
           );
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS node_contributors(
           user TEXT,
           node TEXT,
           UNIQUE(user, node)
           );
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS registrations(
           id TEXT PRIMARY KEY,
           title TEXT,
           date_registered TEXT
           );
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS registration_contributors(
           user TEXT,
           node TEXT,
           UNIQUE(user, node)
           );
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS preprints(
           id TEXT PRIMARY KEY,
           title TEXT,
           date_published TEXT
           );
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS preprint_contributors(
           user TEXT,
           node TEXT,
           UNIQUE(user, node)
           );
    """
)

conn.commit()
conn.close()

