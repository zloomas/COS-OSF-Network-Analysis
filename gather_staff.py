import sqlite3
from config import db_name, seed_project, staff_insert, cos_alumni
from user_functions import map_reduce_get_user_resources, load_user_resources
from collect_data import get_seed_projects


def main():
    """
    Using info gathered from staff and alumni pages on COS website,
    try to verify that we've identified as many current and former staff as easily possible.
    Complete gaps in COS staff data by selecting staff missing from the COS OSF page and collecting their project data.
    
    :return: None
    """
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

    cur.execute(
        """
        SELECT id
          FROM cos_staff
         WHERE id NOT IN (SELECT user FROM node_contributors WHERE node=?) AND
               current=1;
        """,
        (seed_project,)
    )
    missing = cur.fetchall()

    conn.close()

    missing = [m[0] for m in missing]

    for ix, guid in enumerate(missing):
        print(f'fetching nodes for user {ix} - {guid}')
        nodes = map_reduce_get_user_resources(guid, 'nodes')
        load_user_resources(nodes, 'nodes')

    # gather node guids from newly collected user nodes to enhance with additional data
    get_seed_projects()


if __name__ == '__main__':
    main()
