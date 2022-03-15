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
               cos.current
          FROM users u
          LEFT JOIN cos_staff cos ON u.id=cos.id
         ORDER BY u.id;
        """
    )
    users = cur.fetchall()

    conn.close()

    users_df = pd.DataFrame(users, columns=['guid', 'full_name', 'is_cos'])

    contributors_ = {n[0]: [] for n in nodes}

    for c in contributors:
        contributors_[c[1]].append(c[0])

    edges = []

    for node, users in contributors_.items():
        for edge in itertools.combinations(users, 2):
            edges.append((edge[0], edge[1], node))

    edges_df = pd.DataFrame(edges, columns=['user_a', 'user_b', 'project_guid'])

    return users_df, edges_df


def assign_edge_type(row, ref):
    """
    Determines whether given edge (provided as row in dataframe with at least two columns of users, user_a and user_b)
    is composed of two internal nodes, one internal and one external node, or two external nodes. Requires reference
    list of internal nodes. Intended to be used with pandas.DataFrame.apply.

    :param row: row in dataframe with at least two columns of users, user_a and user_b
    :param ref: reference list of internal nodes
    :return: str, edge type, one of 'internal', 'mixed_a' (user_a is internal), 'mixed_b' (user_a is internal), 'external'
    """
    a = row['user_a'] in ref
    b = row['user_b'] in ref

    if a and b:
        edge_type = 'internal'
    elif a and not b:
        edge_type = 'mixed_a'
    elif not a and b:
        edge_type = 'mixed_b'
    else:
        edge_type = 'external'

    return edge_type

