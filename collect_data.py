import sqlite3
from config import db_name, seed_project
from multiprocessing import Pool
from math import ceil
from project_functions import get_project_record, load_project_record, map_get_project_record
from user_functions import map_reduce_get_user_resources, load_user_resources


def get_seed_users():
    """
    Identify COS staff from COS OSF project (https://osf.io/api6f/), load user profiles into DB.

    :return: None
    """

    # gather and data from primary COS staff OSF project
    initial_project = get_project_record(seed_project)
    load_project_record(initial_project)

    # identify COS staff based on those listed on staff project

    users = [u['user'][0] for u in initial_project['users']]

    for ix, guid in enumerate(users):
        print(f'fetching nodes for user {ix} - {guid}')
        nodes = map_reduce_get_user_resources(guid, 'nodes')
        load_user_resources(nodes, 'nodes')


def get_seed_projects(num_processes=2):
    """
    Using nodes gathered from staff list from initial project, gather contributors and child nodes.

    :param num_processes: how many processes to instantiate in process pool
    :return: None
    """
    # gather node guids from collected user nodes to enhance with additional data
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    # refine to be nodes not in known projects
    cur.execute("""
                SELECT id
                  FROM nodes
                 WHERE id NOT IN (SELECT parent from node_relations) AND
                       id NOT IN (SELECT child from node_relations) AND
                       id NOT IN (SELECT node from node_contributors);
                """)
    nodes = cur.fetchall()

    conn.close()

    nodes = [u[0] for u in nodes]

    chunk_len = ceil(len(nodes) / num_processes)

    chunks = [nodes[i:i + chunk_len] for i in range(0, len(nodes), chunk_len)]

    with Pool(num_processes) as pool:
        pool.map(map_get_project_record, chunks)


def main():
    import db_setup
    get_seed_users()
    get_seed_projects()


if __name__ == '__main__':
    main()
