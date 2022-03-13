import requests
import sqlite3
from config import base_url, headers, db_name
from user_functions import process_user_socials, process_user_education, process_user_employment, load_user_profile


def get_project(guid, params=None):
    """
    Given project node GUID, get node data from OSF. Prints errors to console if request fails.

    :param guid: OSF GUID of a project
    :param params: additional parameters to pass to request
    :return: dictionary, data key of json response or empty if response failed
    """

    response = requests.get(base_url + '/nodes/' + guid, headers=headers, params=params)

    if response.ok:
        resp_json = response.json()['data']
    else:
        print(f'nodes request failed at {response.url}: {response.status_code} - {response.reason}')
        resp_json = {}

    return resp_json


def process_project_tags(response_json):
    """
    Given response JSON of request to OSF node, gather all tags associated with project.
    Prepares list of tuples for insertion into DB.
    Intended to be used with output of get_project().

    :param response_json: content of 'data' key from project (node) response
    :return: list of tuples of node tag data (id, tag)
    """
    tags = response_json['attributes']['tags']
    tags_insert = [None for _ in range(len(tags))]

    if tags:
        guid = response_json['id']

        for ix, t in enumerate(tags):
            tags_insert[ix] = (guid, t)

    return tags_insert


def process_project_children(response_json):
    """
    Given response JSON of request to OSF node with embedded children param, gather all child nodes.
    Prepares list of tuples for insertion into DB.
    Makes additional requests as necessary to collect additional results if more than one page of child nodes exists.
    Intended to be used with output of get_project().

    :param response_json: content of 'data' key from project (node) response
    :return: list of tuples of form (parent, child) for insertion into DB
    """

    try:
        num_children = response_json['embeds']['children']['links']['meta']['total']
    except KeyError:
        print(f'missing embedded children in response_json at {response_json["id"]}')
        num_children = 0

    children_insert = [None for _ in range(num_children)]
    nodes_insert = [None for _ in range(num_children)]

    if num_children:
        parent = response_json['id']
        child_ix = 0
        node_ix = 0

        for child in response_json['embeds']['children']['data']:
            children_insert[child_ix] = (parent, child['id'])
            child_ix += 1

            nodes_insert[node_ix] = (child['id'], child['attributes']['title'], child['attributes']['date_created'])
            node_ix += 1

        next_page = response_json['embeds']['children']['links']['next']

        while next_page is not None:
            response = requests.get(next_page, headers=headers)
            if not response.ok:
                print(f'node children request failed at {response.url}: {response.status_code} - {response.reason}')
                print('exiting node children pagination requests')
                break
            else:
                response_json = response.json()['data']

            for child in response_json['embeds']['children']['data']:
                children_insert[child_ix] = (parent, child['id'])
                child_ix += 1

                nodes_insert[node_ix] = (child['id'], child['attributes']['title'], child['attributes']['date_created'])
                node_ix += 1

            next_page = response_json['embeds']['children']['links']['next']

    return children_insert, nodes_insert


def process_project_contributors(response_json):
    """
    Given response JSON of request to OSF node with embedded contributors param, gather all contributors.
    Prepares tuple of lists of contributors and user profiles for insertion into DB.
    Makes additional requests as necessary to collect additional results if more than one page of contributors exists.
    Intended to be used with output of get_project().

    :param response_json: content of 'data' key from project (node) response
    :return: tuple,
             0: list of contributors tuples of form (user, node) for insertion into node_contributors table
             1: list of user profiles of form (id, full_name, date_created) for insertion into users table
    """
    try:
        num_contributors = response_json['embeds']['contributors']['links']['meta']['total']
    except KeyError:
        print(f'missing embedded contributors in response_json at {response_json["id"]}')
        num_contributors = 0

    contributors_insert = [None for _ in range(num_contributors)]
    user_profiles = [None for _ in range(num_contributors)]

    if num_contributors:
        this_node = response_json['id']
        contributors_ix = 0
        users_ix = 0

        for contrib in response_json['embeds']['contributors']['data']:
            this_user = contrib['embeds']['users']['data']
            contributors_insert[contributors_ix] = (this_user['id'], this_node)
            contributors_ix += 1

            user_insert = dict()

            user_insert['user'] = (
                this_user['id'],
                this_user['attributes']['full_name'],
                this_user['attributes']['date_registered']
            )
            user_insert['social'] = process_user_socials(this_user)
            user_insert['employment'] = process_user_employment(this_user)
            user_insert['education'] = process_user_education(this_user)

            user_profiles[users_ix] = user_insert
            users_ix += 1

        next_page = response_json['embeds']['contributors']['links']['next']

        while next_page is not None:
            response = requests.get(next_page, headers=headers)
            if not response.ok:
                print(f'node contributors request failed at {response.url}: {response.status_code} - {response.reason}')
                print('exiting node contributor pagination requests')
                break
            else:
                response_json = response.json()

            for contrib in response_json['data']:
                this_user = contrib['embeds']['users']['data']
                contributors_insert[contributors_ix] = (this_user['id'], this_node)
                contributors_ix += 1

                user_insert = dict()

                user_insert['user'] = (
                    this_user['id'],
                    this_user['attributes']['full_name'],
                    this_user['attributes']['date_registered']
                )
                user_insert['social'] = process_user_socials(this_user)
                user_insert['employment'] = process_user_employment(this_user)
                user_insert['education'] = process_user_education(this_user)

                user_profiles[users_ix] = user_insert
                users_ix += 1

            next_page = response_json['links']['next']

    return contributors_insert, user_profiles


def get_project_record(guid):
    """

    :param guid:
    :return:
    """
    response_json = get_project(guid, params={'embed': ['children', 'contributors']})

    project_insert = dict()

    children, new_nodes = process_project_children(response_json)
    contributors, new_users = process_project_contributors(response_json)

    project_insert['tags'] = process_project_tags(response_json)
    project_insert['children'] = children
    project_insert['nodes'] = new_nodes
    project_insert['contributors'] = contributors
    project_insert['users'] = new_users

    return project_insert


def load_project_record(project_insert):
    """
    Given OSF project data, insert or replace user data in appropriate tables in DB.
    Intended to be used with output of get_project_record().

    :param project_insert: dictionary from get_project_record(),
    expects keys: 'tags', 'children', 'nodes', 'contributors', 'users'
    :return: None
    """

    if not project_insert:
        print('no data in project_insert, exiting process')
        return

    conn = sqlite3.connect(db_name)

    if project_insert['tags']:
        conn.executemany(
            "INSERT OR REPLACE INTO node_tags(id, tag) VALUES (?, ?)",
            project_insert['tags']
        )
        conn.commit()

    if project_insert['children']:
        conn.executemany(
            "INSERT OR REPLACE INTO node_relations(parent, child) VALUES (?, ?)",
            project_insert['children']
        )
        conn.commit()

    if project_insert['nodes']:
        conn.executemany(
            "INSERT OR REPLACE INTO nodes(id, title, date_created) VALUES (?, ?, ?)",
            project_insert['nodes']
        )
        conn.commit()

    if project_insert['contributors']:
        conn.executemany(
            "INSERT OR REPLACE INTO node_contributors(user, node) VALUES (?, ?)",
            project_insert['contributors']
        )
        conn.commit()
    conn.close()

    for u in project_insert['users']:
        load_user_profile(u)
