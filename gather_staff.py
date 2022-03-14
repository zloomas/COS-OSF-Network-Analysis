import sqlite3
from config import db_name, staff_insert, cos_alumni


# using staff and alumni pages from COS website,
# try to verify that we've identified as many current and former staff as easily possible
def main():
    find_alumni = [(name,) for name in cos_alumni]

    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.executemany(
        "INSERT OR REPLACE INTO cos_staff(id, current) VAlUES (?, ?)",
        staff_insert
    )
    conn.commit()

    alumni = []
    for name in find_alumni:
        cur.execute(
            "SELECT * FROM users WHERE full_name = ?",
            name
        )
        alumni.append(cur.fetchall())

    alumni_insert = [(a[0][0], 0) for a in alumni if len(a)]

    cur.executemany(
        "INSERT OR REPLACE INTO cos_staff(id, current) VAlUES (?, ?)",
        alumni_insert
    )
    conn.commit()

    conn.close()


if __name__ == '__main__':
    main()
