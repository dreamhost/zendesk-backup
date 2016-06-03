from bs4 import BeautifulSoup
import unicodedata
import requests
import sys
import os
import json
import cloudfiles
from datetime import datetime
import tarfile
import codecs

def sanitize_filename(filename):
    filename = filename.replace('/', '')
    filename = filename.replace('\0', '')
    return filename

def download_articles(zendesk_domain, backup_loc, email=None, password=None):
    sections = get_sections(zendesk_domain, email, password)
    categories = get_categories(zendesk_domain, email, password)
    categories_dict = {}
    for category in categories['categories']:
        categories_dict[category['id']] = category

    for section in sections['sections']:
        category_dir = os.path.join(backup_loc, str(section['category_id']) + " " +
            sanitize_filename(categories_dict[section['category_id']]['name'])
        )
        if not os.path.isdir(category_dir):
            os.mkdir(category_dir, 0700)

        file_directory = os.path.join(category_dir, str(section['id']) + " " +
            sanitize_filename(section['name'])
        )
        if not os.path.isdir(file_directory):
            os.mkdir(file_directory, 0700)

        articles = get_articles(zendesk_domain, section['id'], email, password)
        for article in articles['articles']:
            file_name = os.path.join(file_directory, str(article['id']) + " " +
                sanitize_filename(article['title']) + '.json'
            )
            file_name = unicodedata.normalize('NFKC', file_name).encode('ascii', 'ignore')
            print "Writing file " + file_name
            with codecs.open(file_name, 'w', encoding='utf-8') as f:
                f.write(json.dumps(article))
        f.close()

def get_articles(zendesk_domain, section_id, email=None, password=None):
    session = requests.Session()
    if email and password:
        session.auth = (email, password)

    url = zendesk_domain + "/api/v2/help_center/sections/" + str(section_id) + "/" + "articles.json?per_page=100"
    response_raw = session.get(url)
    articles = json.loads(response_raw.content)
    next_page = articles['next_page']
    while next_page is not None:
        page_raw = session.get(next_page)
        page = json.loads(page_raw.content)
        articles['articles'] = articles['articles'] + page['articles']
        next_page = page['next_page']

    return articles

def get_sections(zendesk_domain, email=None, password=None):
    session = requests.Session()
    if email and password:
        session.auth = (email, password)

    response_raw = session.get(zendesk_domain + "/api/v2/help_center/sections.json?per_page=100")
    sections = json.loads(response_raw.content)
    next_page = sections['next_page']
    while next_page is not None:
        page_raw = session.get(next_page)
        page = json.loads(page_raw.content)
        sections['sections'] = sections['sections'] + page['sections']
        next_page = page['next_page']

    return sections

def get_categories(zendesk_domain, email=None, password=None):
    session = requests.Session()
    if email and password:
        session.auth = (email, password)

    response = session.get(zendesk_domain + "/api/v2/help_center/categories.json?per_page=1000")
    categories = json.loads(response.content)
    return categories

def upload_to_dho(dho_user, dho_key, backup_loc):
    conn = cloudfiles.get_connection(
        username=dho_user,
        api_key=dho_key,
        authurl='https://objects-us-west-1.dream.io/auth',
    )

    container = create_container(conn)

    for category in os.listdir(backup_loc):
        category_path = os.path.join(backup_loc, category)
        for section in os.listdir(category_path):
            section_path = os.path.join(category_path, section)
            for file_name in os.listdir(section_path):
                file_path = os.path.join(section_path, file_name)
                print "uploading " + file_path
                obj = container.create_object(file_path)
                uploaded = False
                i = 0
                while i <= 4 and uploaded == False:
                    try:
                        obj.load_from_filename(file_path)
                        uploaded = True

                    except ssl.SSLError:
                        if i < 4:
                            print "Failed to upload " + file_path + ", trying again"
                            i = i + 1

                        else:
                            print "Failed to upload 5 times, aborting"
                            sys.exit(1)


def create_container(conn):
    created = False
    i = 0
    now = datetime.now()
    container_name = "kbbackup"
    while created == False and i <= 4:
        try:
            container = conn.create_container(container_name)
            created = True
        except ssl.SSLError:
            i = i + 1

    return container

def create_tar(backup_loc):
    tar_name = backup_loc + ".tar"
    with tarfile.open(tar_name, "w:gz") as tar:
        tar.add(backup_loc, arcname=os.path.basename(backup_loc))

    return tar_name

# Grab variables for authentication and the url from the environment
env = os.environ

try:
    email = env['EMAIL']
except:
    email = None

try:
    password = env['ZENDESK_PASS']
except:
    password = None

try:
    dho_key = env['DHO_KEY']
except:
    print("The environment variable 'DHO_KEY' is not set, please set it to your DreamObjects Key")

try:
    dho_user = env['DHO_USER']
except:
    print("The environment variable 'DHO_USER' is not set, please set it to your DreamObjects User")

try:
    zendesk_domain = env['ZENDESK_URL']
except:
    zendesk_domain = input("Enter the zendesk url: ")

now = datetime.now()
backup_loc = str(now.year)
if not os.path.isdir(backup_loc):
    os.mkdir(backup_loc, 0700)

backup_loc = os.path.join(backup_loc, str(now.month))
if not os.path.isdir(backup_loc):
    os.mkdir(backup_loc, 0700)

backup_loc = os.path.join(backup_loc, str(now.day))
if not os.path.isdir(backup_loc):
    os.mkdir(backup_loc, 0700)

backup_loc = os.path.join(backup_loc, str(now.hour))
if not os.path.isdir(backup_loc):
    os.mkdir(backup_loc, 0700)

download_articles(zendesk_domain, backup_loc, email, password)
upload_to_dho(dho_user, dho_key, backup_loc)
