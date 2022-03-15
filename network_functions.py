import sqlite3
import itertools
import pandas as pd
from config import db_name


def create_network():
    """
    Gathers all users and their co-collaborations from DB.
    
    :return: tuple, three dataframes: 
             (1) users (network nodes) with columns: 'guid', 'full_name', 'is_cos' (None if non-COS, 0 if former and 1 if current)
             (2) nodes (OSF projects) with columns: 'root', 'base'
             (2) edges with columns: 'internal', 'external', 'project_guid'
    """
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
          FROM node_contributors
         ORDER BY node, user;
        """
    )
    contributors = cur.fetchall()

    cur.execute(
        """
        SELECT nr2.parent,
               nr1.parent,
               nr1.child,
               nr3.child
          FROM node_relations nr1
          LEFT JOIN node_relations AS nr2
               ON nr1.parent = nr2.child
          LEFT JOIN node_relations AS nr3
               ON nr1.child = nr3.parent
         ORDER BY nr2.parent;
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
    cos_staff = users_df[users_df.is_cos.notna()].guid.values
    
    node_relations = []
    for n in nodes:
        node_type = None
        n_filter = list(filter(lambda x: x is not None, n))
        if len(n_filter) == 2:
            if len(set(n_filter)) == 1:
                node_type = 'root'
            else:
                node_type = 'child'
        elif len(n_filter) == 3:
            node_type = 'grandchild'
        
        if node_type:
            node_relations.append((n_filter[0], n_filter[-1], node_type))
        else:
            print('uh oh')
            print(n)
        
    nodes_df = pd.DataFrame(node_relations, columns=['root', 'base', 'type']).drop_duplicates().reset_index()

    contributors_ = {n: [] for n in nodes_df.base.unique()}

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

    return users_df, nodes_df, edges_df
