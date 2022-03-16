# COS-OSF-Network-Analysis

Independent project to analyze the collaboration network of current COS staff. 
Involves gathering data via OSF API, storing and querying collected data in a SQLite database, and conducting analyses in Jupyter notebook.
[Notebook](COS_OSF_collaboration_network.ipynb) includes information regarding methods and key findings.

### Contents of this repository

#### Data collection and storage
    
To reproduce the data collection pipeline, run `collect_data.py`, `gather_staff.py`, then run `get_next_level()` (in `collect_data.py`). 
Depending on your setup, you may be able to take advantage of parallelization of requests to a greater extent than I was; 
just adjust `num_processes` wherever it appears as a parameter in the data collection functions.

##### [db_setup.py](db_setup.py)

Creates initial database and tables.

##### [user_functions.py](user_functions.py)

Defines functions to:
- request user OSF profile
- request user nodes, registrations, and preprints
- process profile to extract name, date registered, socials, employment, and education
- process resources to extract title and date created, registered, or published, respectively
- load user data into DB

##### [project_functions.py](project_functions.py)

Defines functions to:
- request node data from OSF
- request node contributors and child nodes
- process node data to extract title, tags, and date created
- process contributors to extract user profiles
- process chid nodes to extract title and date created
- load project data into DB

##### [collect_data.py](collect_data.py)
    
Uses functions from user_functions and project_functions to collect data. 
Running as a script will collect initial data for users on seed project, their profiles and projects, and the contributors and child nodes of their projects. 
`get_next_level()` must be run separately to collect the second degree projects and contributors, 
and may be run iteratively to continue to build the network out to further and further degrees of separation from current COS staff.

##### [gather_staff.py](gather_staff.py)

Requires two resources in config: (1) a list of COS alumni (available on COS website), 
(2) a list of tuples of COS staff user profile entries for the cos_staff table in DB.

Attempts to identify COS alumni and updates additional current staff that were found to be missing from seed project. 
Fills in initial data collection (user profile and root projects) for newly added staff to curate a complete record for all current COS staff.

#### Other

Supplemental scripts are also used in the course of conducting this analysis.
    
##### config.py

The config file must contain:
- db_name: file name of local DB
- seed_project: OSF GUID of initial project used to identify starting users
- OSF_PAT: OSF PAT for API authentication
- base_url: OSF API base URL - 'https://api.osf.io/v2'

To complete records for current COS staff, it must also contain:
- cos_alumni: a list of COS alumni (available on COS website)
- staff_insert: a list of tuples of COS staff user profile entries for the cos_staff table in DB
    
##### [network_functions.py](network_functions.py)

Contains one function, `create_network()` which queries DB to gather the majority of relevant data for analysis 
and returns pandas DataFrames for convenient use thereafter.
