import re
import requests
import sqlite3
import functools
from multiprocessing import Pool
from math import ceil
from config import base_url, headers


# for some user, collect: name, date_registered, socials, employment, education
def get_user(guid):
    """
    Given user GUID, get user profile data from OSF. Prints errors to console if request fails.

    :param guid: OSF GUID of a user profile
    :return: dictionary, data key of json response or empty if response failed
    """

    response = requests.get(base_url + '/users/' + guid, headers=headers)

    if response.ok:
        resp_json = response.json()['data']
    else:
        print(f'users request failed at {response.url}: {response.status_code} - {response.reason}')
        resp_json = {}

    return resp_json


def process_user_socials(response_json):
    """
    Given OSF user response dictionary, extract user socials and prepare list of tuples for insertion into DB.
    Intended to be used with get_user().

    :param response_json: content of 'data' key from user profile response
    :return: list of tuples of form (guid, platform, username) for insertion into DB
    """

    guid = response_json['id']

    socials = []
    # if socials are available, add each to socials list as tuple (guid, platform, username)
    for key, val in response_json['attributes']['social'].items():
        # require non-null username/ID for each platform, ignore if empty string
        # websites are returned as a list and must be parsed into discrete entries
        if key == 'profileWebsites' and len(val):
            for site in val:
                if len(site):
                    socials.append((guid, key, site))
        else:
            if len(val):
                socials.append((guid, key, val))

    return socials


def process_user_employment(response_json):
    """
    Given OSF user response dictionary, extract user employment and prepare list of tuples for insertion into DB.
    Intended to be used with get_user().

    :param response_json: content of 'data' key from user profile response
    :return: list of tuples of form (guid, title, institution, start_year, end_year, ongoing) for insertion into DB
    """

    guid = response_json['id']

    employment = []
    # if employment history is available, add each position to employment list as tuple with form:
    # (guid, title, institution, start_year, end_year, ongoing)
    for job in response_json['attributes']['employment']:
        # require title and institution, if either is empty skip entry
        title = job['title']
        if not len(title):
            continue

        institution = job['institution']
        if not len(institution):
            continue

        # require numeric year values for start and end dates
        try:
            start_year = int(job['startYear'])
        except ValueError:
            start_year = None

        ongoing = job['ongoing']

        # no end date expected if job is ongoing
        if ongoing:
            end_year = None
        else:
            try:
                end_year = int(job['endYear'])
            except ValueError:
                end_year = None

        employment.append(
            (guid, title, institution, start_year, end_year, ongoing)
        )

    return employment


def process_user_education(response_json):
    """
    Given OSF user response dictionary, extract user education and prepare list of tuples for insertion into DB.
    Intended to be used with get_user().

    :param response_json: content of 'data' key from user profile response
    :return: list of tuples of form (guid, degree, institution, start_year, end_year, ongoing) for insertion into DB
    """
    guid = response_json['id']

    education = []
    for e in response_json['attributes']['education']:
        # require degree and institution, if either is empty skip entry
        degree = e['degree']
        if not len(degree):
            continue

        institution = e['institution']
        if not len(institution):
            continue

        # require numeric year values for start and end dates
        try:
            start_year = int(e['startYear'])
        except ValueError:
            start_year = None

        ongoing = e['ongoing']

        # no end date expected if degree is ongoing
        if ongoing:
            end_year = None
        else:
            try:
                end_year = int(e['endYear'])
            except ValueError:
                end_year = None

        education.append(
            (guid, degree, institution, start_year, end_year, ongoing)
        )

    return education


def process_user_profile(guid):
    """
    Given user GUID, get user profile data from OSF. Parse to create lists of profile information regarding
    social media platforms, education, and employment history.

    :param guid: OSF GUID of a user profile
    :return: dictionary with keys 'user', 'social', 'employment', 'education', where each has a list of tuples
    for insertion into DB, or an empty list if data is unavailable.
    """

    user_resp = get_user(guid)
    user_insert = {}

    if not user_resp:
        return user_insert

    user_insert['user'] = (
        user_resp['id'],
        user_resp['attributes']['full_name'],
        user_resp['attributes']['date_registered']
    )
    user_insert['social'] = process_user_socials(user_resp)
    user_insert['employment'] = process_user_employment(user_resp)
    user_insert['education'] = process_user_education(user_resp)

    return user_insert


def load_user_profile(user_insert):
    """
    Given OSF user data, insert or replace user data in appropriate tables in DB.
    Intended to be used with process_user_profile().

    :param user_insert: dictionary from process_user_profile(), expects keys: 'user', 'social', 'employment', 'education'
    :return: None
    """

    conn = sqlite3.connect('lt_osf.sqlite')
    if not user_insert:
        print('no data in user_insert, exiting process')
        return

    if user_insert['user']:
        conn.execute(
            "INSERT OR REPLACE INTO users(id, full_name, date_created) VALUES (?, ?, ?)",
            user_insert['user']
        )
        conn.commit()

    if user_insert['social']:
        conn.executemany(
            "INSERT OR REPLACE INTO socials(id, platform, name) VALUES (?, ?, ?)",
            user_insert['social']
        )
        conn.commit()

    if user_insert['employment']:
        conn.executemany(
            """
            INSERT OR REPLACE INTO jobs(id, title, institution, start_year, end_year, ongoing) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            user_insert['employment']
        )
        conn.commit()

    if user_insert['education']:
        conn.executemany(
            """
            INSERT OR REPLACE INTO education(id, degree, institution, start_year, end_year, ongoing) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            user_insert['education']
        )
        conn.commit()

    conn.close()


def get_user_resources(guid, resource_type, page):
    """
    Given user GUID, get one page of nodes of some type from OSF

    :param guid: OSF GUID of a user profile
    :param resource_type: one of 'nodes', 'registrations', 'preprints' to indicate what type of resource to request
    from OSF
    :param page: int, which page of results to request
    :return: response json if response is successful, else empty dictionary
    """
    resp_json = {}

    if resource_type not in ['nodes', 'registrations', 'preprints']:
        print(f'{resource_type} is not supported, must be one of nodes, registrations, or preprints')
        print(f'exiting process at get_user_resources({guid}, {resource_type}, {page})')
        return resp_json

    nodes_url = f'{base_url}/users/{guid}/{resource_type}'
    resp = requests.get(nodes_url, headers=headers, params={'page': page})

    if resp.ok:
        resp_json = resp.json()
    else:
        print(f'{resource_type} request failed at {resp.url}: {resp.status_code} - {resp.reason}')

    return resp_json


def concat_lists(list_a, list_b):
    """
    Concatenate two lists. Intended to be used as reduce function in map_reduce_get_user_resources().

    :param list_a: a list
    :param list_b: a list
    :return: concatenated list of contents of list_a and list_b
    """
    return list_a + list_b


def map_get_user_resources(guid, resource_type, page_range):
    """
    Maps get_user_resources() to provided page_range.
    Processes resource data to prepare for insertion into DB.

    :param guid: OSF GUID of a user profile
    :param resource_type: one of 'nodes', 'registrations', 'preprints' to indicate what type of resource to request
    from OSF. also used to determine which date field to gather from response.
    :param page_range: iterable of integers representing pages to be passed to get_user_resources()
    :return: list of projects as tuples with form (guid, title, date_field)
    """

    if resource_type == 'nodes':
        date_field = 'date_created'
    elif resource_type == 'registrations':
        date_field = 'date_registered'
    elif resource_type == 'preprints':
        date_field = 'date_published'
    else:
        print('resource_type is not supported, exiting process')
        return

    projects = [None for _ in range(len(page_range)*10)]
    ix = 0

    for page in page_range:

        response = get_user_resources(guid, resource_type, page)
        if not response:
            print(f'empty project response for user {guid} on page {page}')
            print('exiting process')
            break

        for node in response['data']:
            projects[ix] = (node['id'], node['attributes']['title'], node['attributes'][date_field])
            ix += 1

    return projects


def map_reduce_get_user_resources(guid, resource_type, num_processes=2):
    """
    Gathers all nodes of some type for a given user.
    Makes initial request to user/{guid}/{resource_type} endpoint to determine how many pages of results to expect.
    Maps page range to map_get_user_resources().
    Reduces output to list of nodes ready for insertion into DB.

    :param guid: OSF GUID of a user profile
    :param resource_type: one of 'nodes', 'registrations', 'preprints' to indicate what type of resource to request
    from OSF. also used to determine which date field to gather from response.
    :param num_processes: how many processes to instantiate in process pool
    :return: list of nodes as tuples with form (guid, title, date_field)
    """

    response = get_user_resources(guid, resource_type, page=1)

    if not response:
        return

    if resource_type == 'nodes':
        date_field = 'date_created'
    elif resource_type == 'registrations':
        date_field = 'date_registered'
    elif resource_type == 'preprints':
        date_field = 'date_published'
    else:
        print('resource_type is not supported, exiting process')
        return

    initial_nodes = [None for _ in range(10)]
    ix = 0

    for node in response['data']:
        initial_nodes[ix] = (node['id'], node['attributes']['title'], node['attributes'][date_field])
        ix += 1

    num_pages = ceil(response['links']['meta']['total'] / 10)

    if num_pages == 1:
        return initial_nodes

    pages = [num for num in range(2, num_pages + 1)]

    chunk_len = ceil(len(pages) / num_processes)

    chunks = [(guid, resource_type, pages[i:i + chunk_len]) for i in range(0, len(pages), chunk_len)]

    with Pool(num_processes) as pool:
        chunk_results = pool.starmap(map_get_user_resources, chunks)

    nodes = functools.reduce(concat_lists, chunk_results)

    resources = initial_nodes + nodes

    resources = list(filter(lambda x: x is not None, resources))

    return resources


def load_nodes(resp_data, conn):
    """

    :param resp_data: list of nodes from data key of of OSF API response for user nodes
    :param conn:
    :return:
    """
    if not resp_data:
        return

    nodes_insert = []
    for node in resp_data:
        nodes_insert.append(
            (
                node['id'],
                node['attributes']['title'],
                node['attributes']['date_created']
            )
        )

    conn.executemany(
        "INSERT OR REPLACE INTO nodes(id, title, date_created) VALUES (?, ?, ?)",
        nodes_insert
    )
    conn.commit()


# for some user, collect all project GUIDs
def get_user_nodes(guid):
    """
    Given user GUID, get all nodes for user from OSF

    :param guid: OSF GUID of a user profile
    :return: None
    """

    nodes_url = base_url + '/users/' + guid + '/nodes'
    resp = requests.get(nodes_url, headers=headers)

    if resp.ok:
        resp_dict = resp.json()
        last_link = resp_dict['links']['last']
        if last_link is not None:
            num_pages = int(re.findall(r'[0-9]+$', last_link)[0])
        else:
            num_pages = 1
    else:
        print(f'{guid} nodes page 1 request failed: {resp.reason}')
        return

    load_nodes(resp_dict['data'], conn)

    if num_pages > 1:
        for page in range(2, num_pages + 1):
            page_resp = requests.get(nodes_url, params={'page': page}, headers=headers)
            if page_resp.ok:
                load_nodes(page_resp.json()['data'], conn)
            else:
                print(f'{guid} nodes page {page} request failed: {page_resp.reason}')
                continue

# for some user, collect all registration GUIDs
# for some user, collect all preprint GUIDs


def main():
    from config import lt_guids

    for guid in lt_guids.values():
        user = process_user_profile(guid)
        load_user_profile(user)


if __name__ == '__main__':
    main()
