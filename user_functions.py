import re
import requests
from config import base_url, headers


# for some user, collect: date_registered, socials, employment, education
def get_user_profile(guid, conn):
    """
    Given user GUID and database connection, get user profile data from OSF, add to appropriate tables in database.

    :param guid: OSF GUID of a user profile
    :param conn: SQLite3 Connection
    :return: None
    """

    resp = requests.get(base_url + '/users/' + guid, headers=headers)

    if resp.ok:
        resp_dict = resp.json()['data']['attributes']
    else:
        print(f'{guid} users request failed: {resp.reason}')
        return

    conn.execute(
        "INSERT OR REPLACE INTO users(id, full_name, date_created) VALUES (?, ?, ?)",
        (guid, resp_dict['full_name'], resp_dict['date_registered'])
    )
    conn.commit()

    # if socials are available, add each to socials table
    socials = resp_dict['social']
    if socials:
        # generate list of entires as tuples
        socials_insert = []
        for key, val in socials.items():
            # require username/ID for each platform, ignore if empty
            # websites are returned as a list and must be parsed into discrete entries
            if key == 'profileWebsites' and len(val):
                for site in val:
                    if len(site):
                        socials_insert.append((guid, key, site))
            else:
                if len(val):
                    socials_insert.append((guid, key, val))

        if socials_insert:
            conn.executemany(
                "INSERT OR REPLACE INTO socials(id, platform, name) VALUES (?, ?, ?)",
                socials_insert
            )
            conn.commit()

    # if job history is available, add each position to jobs table
    employment = resp_dict['employment']
    if employment:
        # generate list of entires as tuples
        jobs_insert = []
        for job in employment:
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

            jobs_insert.append(
                (guid, title, institution, start_year, end_year, ongoing)
            )

        if jobs_insert:
            conn.executemany(
                """
                INSERT OR REPLACE INTO jobs(id, title, institution, start_year, end_year, ongoing) 
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                jobs_insert
            )
            conn.commit()

    # if education history is available, add each position to education table
    education = resp_dict['education']
    if education:
        # generate list of entires as tuples
        education_insert = []
        for e in education:
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

            education_insert.append(
                (guid, degree, institution, start_year, end_year, ongoing)
            )

        if education_insert:
            conn.executemany(
                """
                INSERT OR REPLACE INTO education(id, degree, institution, start_year, end_year, ongoing) 
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                education_insert
            )
            conn.commit()


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
def get_user_nodes(guid, conn):
    """
    Given user GUID and database connection, get all nodes for user from OSF, add to appropriate tables in database.

    :param guid: OSF GUID of a user profile
    :param conn: SQLite3 Connection
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
