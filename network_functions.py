import sqlite3
import itertools
import pandas as pd
from config import db_name


def create_network():
    """
    Gathers all users and their co-collaborations from DB.
    
    :return: tuple, three dataframes: 
             (1) users (network nodes) with columns: 'guid', 'full_name', 'is_cos' (None if non-COS, 0 if former and 1 if current)
             (2) edges with columns: 'internal', 'external', 'project_guid'
    """
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    
    cur.execute(
        """
        SELECT u.id,
               u.full_name,
               cos.current
          FROM users u
          LEFT JOIN cos_staff cos ON u.id=cos.id
         ORDER BY u.id;
        """
    )
    users = cur.fetchall()

    cur.execute(
        """
        SELECT node, user
          FROM node_contributors
         ORDER BY node, user;
        """
    )
    contributors = cur.fetchall()

    conn.close()

    users_df = pd.DataFrame(users, columns=['guid', 'full_name', 'is_cos'])
    cos_staff = users_df[users_df.is_cos.notna()].guid.values

    contributor_relations = dict()

    for c in contributors:
        if c[0] in contributor_relations:
            contributor_relations[c[0]].append(c[1])
        else:
            contributor_relations[c[0]] = [c[1]]

    edges = []

    for node, users in contributor_relations.items():
        for edge in itertools.combinations(users, 2):
            a = edge[0]
            b = edge[1]
            if a in cos_staff and b not in cos_staff:
                edges.append((a, b, node))
            elif a not in cos_staff and b in cos_staff:
                edges.append((b, a, node))

    edges_df = pd.DataFrame(edges, columns=['internal', 'external', 'project_guid'])

    return users_df, edges_df
