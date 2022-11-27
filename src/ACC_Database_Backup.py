from datetime import datetime
import json
from bson.json_util import dumps
import os
from pymongo import MongoClient
from ACC_Credentials import MONGO_LINK
from googleapiclient.http import MediaFileUpload
from util_gdrive import get_gdrive_service

MONGO_CLIENT = MongoClient(MONGO_LINK)
ACC_COLLECTION = MONGO_CLIENT.isda
DESTINATION_FOLDER = 'mongo_backup'
GDRIVE_SERVICE = None
FOLDER_ID = None


def get_date_string():
    return str(datetime.today()).replace("-", "").split(" ")[0]

def upload_to_gdrive(file_name, real_path):
    global GDRIVE_SERVICE
    if GDRIVE_SERVICE is None:
        GDRIVE_SERVICE = get_gdrive_service()

    file_metadata = {
        'name': file_name,
        'parents': [get_gdrive_directory()]
    }
    media = MediaFileUpload(real_path, resumable=True)
    file = GDRIVE_SERVICE.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print("File created, id:", file.get("id"))


def get_backup_directory():
    date_name = get_date_string()
    if not os.path.isdir("backup"):
        os.mkdir("backup")
    dir_name = os.path.join("backup", date_name)
    if not os.path.isdir(dir_name):
        os.mkdir(dir_name)
    return os.path.realpath(dir_name)


def get_gdrive_directory():
    global GDRIVE_SERVICE
    global FOLDER_ID

    if GDRIVE_SERVICE is None:
        GDRIVE_SERVICE = get_gdrive_service()

    if FOLDER_ID is None:
        page_token = None
        response = GDRIVE_SERVICE.files().list(q='mimeType = "application/vnd.google-apps.folder" and name = "{}"'.format(DESTINATION_FOLDER),
                                               spaces='drive',
                                               fields='nextPageToken, files(id, name)',
                                               pageToken=page_token).execute()
        items_list = response.get('items', [])
        print(items_list)
        if not items_list:
            print('Create backup folder')
            folder_metadata = {
                'name': 'mongo_backup',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            file = GDRIVE_SERVICE.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            backup_folder_id = file.get('id')
        else:
            backup_folder_id = items_list[0].get('id')
        
        print(backup_folder_id)
        
        folder_metadata = {
            'name': get_date_string(),
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [backup_folder_id]
        }
        file = GDRIVE_SERVICE.files().create(
            body=folder_metadata,
            fields='id',
        ).execute()
        FOLDER_ID = file.get('id')
    print(FOLDER_ID)
    return FOLDER_ID

def backup_driver_data():
    collections = ACC_COLLECTION.list_collection_names()
    for collection in collections:
        data = list(ACC_COLLECTION[collection].find())
        output_file_name = f"{collection}.json"
        outfile_path = os.path.join(get_backup_directory(), output_file_name)
        with open(outfile_path, "w", encoding="utf-8") as outfile:
            json.dump(json.loads(dumps(data).encode("utf-8")), outfile, indent=2)
        upload_to_gdrive(output_file_name, outfile_path)

if __name__ == '__main__':
    backup_driver_data()
