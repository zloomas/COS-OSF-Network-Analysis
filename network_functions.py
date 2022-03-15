import sqlite3
import itertools
import pandas as pd
from config import db_name


def create_network():
    """
    Gathers all users and their co-collaborations from DB.
    
    :return: tuple, two dataframes: 
             (1) users (nodes) with columns: 'guid', 'full_name', 'is_cos' (None if non-COS, 0 if former and 1 if current)
             (2) edges with columns: 'user_a', 'user_b', 'project_guid'
    """
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
          FROM node_contributors
         WHERE node IN (SELECT parent FROM node_relations)
         ORDER BY node, user;
        """
    )
    contributors = cur.fetchall()

    cur.execute(
        """
        SELECT n.id,
               c.count
          FROM nodes n
          LEFT JOIN (SELECT node, COUNT(user) AS count FROM node_contributors GROUP BY node) AS c
               ON n.id = c.node
         WHERE n.id IN (SELECT parent FROM node_relations)
         ORDER BY n.id;
        """
    )
    nodes = cur.fetchall()

    cur.execute(
        """
        SELECT u.id,
               u.full_name,
               u.date_created,
               cos.current
          FROM users u
          LEFT JOIN cos_staff cos ON u.id=cos.id
         ORDER BY u.id;
        """
    )
    users = cur.fetchall()

    conn.close()

    users_df = pd.DataFrame(users, columns=['guid', 'full_name', 'date_created', 'is_cos'])
    cos_staff = users_df[users_df.is_cos.notna()].guid.values

    contributors_ = {n[0]: [] for n in nodes}

    for c in contributors:
        contributors_[c[1]].append(c[0])

    edges = []

    for node, users in contributors_.items():
        for edge in itertools.combinations(users, 2):
            a = edge[0]
            b = edge[1]
            if a in cos_staff and b not in cos_staff:
                edges.append((a, b, node))
            elif a not in cos_staff and b in cos_staff:
                edges.append((b, a, node))

    edges_df = pd.DataFrame(edges, columns=['internal', 'external', 'project_guid'])

    return users_df, edges_df
