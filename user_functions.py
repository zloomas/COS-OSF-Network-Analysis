import requests
from config import *


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
        print(resp.reason)
        return

    conn.execute(
        "INSERT INTO users(id, full_name, date_created) VALUES (?, ?, ?)",
        (guid, resp_dict['full_name'], resp_dict['date_registered'])
    )
    conn.commit()

    # if socials are available, add each to socials table
    try:
        socials = resp_dict['social']
    except KeyError:
        pass
    else:
        # generate list of entires as tuples
        socials_insert = []
        for key, val in socials.items():
            # websites are returned as a list and must be parsed into discrete entries
            if key == 'profileWebsites':
                for site in val:
                    socials_insert.append((guid, key, site))
            else:
                if len(val):
                    socials_insert.append((guid, key, val))
        conn.executemany(
            "INSERT INTO socials(id, platform, name) VALUES (?, ?, ?)",
            socials_insert
        )
        conn.commit()

    # if job history is available, add each position to jobs table
    try:
        employment = resp_dict['employment']
    except KeyError:
        pass
    else:
        # generate list of entires as tuples
        jobs_insert = []
        for job in employment:
            if 'title' in job:
                title = job['title']
            else:
                title = None

            if 'institution' in job:
                institution = job['institution']
            else:
                institution = None

            if 'startYear' in job:
                start_year = job['startYear']
            else:
                start_year = None

            ongoing = job['ongoing']

            if ongoing:
                end_year = None
            else:
                if 'endYear' in job:
                    end_year = job['endYear']
                else:
                    end_year = None

            jobs_insert.append(
                (guid, title, institution, start_year, end_year, ongoing)
            )

        conn.executemany(
            "INSERT INTO jobs(id, title, institution, start_year, end_year, ongoing) VALUES (?, ?, ?, ?, ?, ?)",
            jobs_insert
        )
        conn.commit()

    # if education history is available, add each position to education table
    try:
        education = resp_dict['education']
    except KeyError:
        pass
    else:
        # generate list of entires as tuples
        education_insert = []
        for e in education:
            if 'degree' in e:
                degree = e['degree']
            else:
                degree = None

            if 'institution' in e:
                institution = e['institution']
            else:
                institution = None

            if 'startYear' in e:
                start_year = e['startYear']
            else:
                start_year = None

            ongoing = e['ongoing']

            if ongoing:
                end_year = None
            else:
                if 'endYear' in e:
                    end_year = e['endYear']
                else:
                    end_year = None

            education_insert.append(
                (guid, degree, institution, start_year, end_year, ongoing)
            )

        conn.executemany(
            "INSERT INTO education(id, degree, institution, start_year, end_year, ongoing) VALUES (?, ?, ?, ?, ?, ?)",
            education_insert
        )
        conn.commit()

# for some user, collect all project GUIDs
# for some user, collect all registration GUIDs
# for some user, collect all preprint GUIDs
