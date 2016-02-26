from bs4 import BeautifulSoup
import requests
import sys
import os
import json
import cloudfiles
from datetime import datetime
import tarfile
from io import open

def download_articles(zendesk_domain, email, password):
    if not os.path.isdir(backup_loc):
        os.mkdir(backup_loc, 0700)

    sections = get_sections(zendesk_domain, email, password)

    for section in sections['sections']:
        category_dir = os.path.join(backup_loc, str(section['category_id']))
        if not os.path.isdir(category_dir):
            os.mkdir(category_dir, 0700)

        file_directory = os.path.join(category_dir, str(section['id']))
        if not os.path.isdir(file_directory):
            os.mkdir(file_directory, 0700)

        articles = get_articles(zendesk_domain, email, password, section['id'])
        for article in articles['articles']:
            file_name = os.path.join(file_directory, str(article['id']))
            with open(file_name, 'w') as f:
                f.write(article['body'])
        f.close()

def get_articles(zendesk_domain, email, password, section_id):
    session = requests.Session()
    session.auth = (email, password)

    url = zendesk_domain + "/api/v2/help_center/sections/" + str(section_id) + "/" + "articles.json?per_page=2000"

    response = session.get(url)
    articles = json.loads(response.content)
    return articles

def get_sections(zendesk_domain, email, password):
    session = requests.Session()
    session.auth = (email, password)
    response = session.get(zendesk_domain + "/api/v2/help_center/sections.json?per_page=1000")
    sections = json.loads(response.content)
    return sections

def upload_to_dho(dho_user, dho_key, backup_loc):
    conn = cloudfiles.get_connection(
        username=dho_user,
        api_key=dho_key,
        authurl='https://objects.dreamhost.com/auth',
    )
    container = create_container(conn)

    create_tar(backup_loc)

def create_container(conn):
    now = datetime.now()
    container_name = str(now.year) + '-' + str(now.month) + '-' + str(now.day) + '-' + str(now.hour)
    container = conn.create_container(container_name)
    return container

def create_tar(backup_loc):
    tar_name = backup_loc + ".tar"
    with tarfile.open(tar_name, "w:gz") as tar:
        tar.add(backup_loc, arcname=os.path.basename(backup_loc))

# Grab variables for authentication and the url from the environment
env = os.environ
backup_loc = 'zendesk-backup'

try:
    email = env['EMAIL']
except:
    print("The environment variable 'EMAIL' is not set, please set it to the email that you use with zendesk")
    sys.exit(1)

try:
    password = env['ZENDESK_PASS']
except:
    print("The environment variable 'ZENDESK_PASS' is not set, please set it to your zendesk password")
    sys.exit(1)

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

#download_articles(zendesk_domain, email, password)
upload_to_dho(dho_user, dho_key)
