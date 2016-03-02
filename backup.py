from bs4 import BeautifulSoup
import requests
import sys
import os
import json
import cloudfiles
from datetime import datetime
import tarfile
from io import open

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
                sanitize_filename(article['title'])
            )
            print "Writing file " + file_name
            with open(file_name, 'w') as f:
                f.write(article['body'])
        f.close()

def get_articles(zendesk_domain, section_id, email=None, password=None):
    session = requests.Session()
    if email and password:
        session.auth = (email, password)

    url = zendesk_domain + "/api/v2/help_center/sections/" + str(section_id) + "/" + "articles.json?per_page=2000"

    response = session.get(url)
    articles = json.loads(response.content)
    return articles

def get_sections(zendesk_domain, email=None, password=None):
    session = requests.Session()
    if email and password:
        session.auth = (email, password)

    response = session.get(zendesk_domain + "/api/v2/help_center/sections.json?per_page=1000")
    sections = json.loads(response.content)
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
        authurl='https://objects.dreamhost.com/auth',
    )
    container = create_container(conn)

    for category in os.listdir(backup_loc):
        category_path = os.path.join(backup_loc, category)
        for section in os.listdir(category_path):
            section_path = os.path.join(category_path, section)
            for file_name in os.listdir(section_path):
                file_path = os.path.join(section_path, file_name)
                print ("uploading " + file_path)
                obj = container.create_object(file_path)
                obj.load_from_filename(file_path)

def create_container(conn):
    now = datetime.now()
    container_name = "kbbackup"
    container = conn.create_container(container_name)
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
