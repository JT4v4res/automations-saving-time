import os

from googleapiclient.discovery import build
from google.oauth2 import service_account
import re
import json

credentials = service_account.Credentials.from_service_account_file('your_service_account_file.json')
document_id = 'your_document_id'

service = build('docs', 'v1', credentials=credentials)

document = service.documents().get(documentId=document_id).execute()

try:
    os.mkdir('texts')
except FileExistsError:
    print('Directory already exists')

document_text = ''

text_title = ''

json_file = {}

to_concat = False

for content in document.get('body').get('content'):
    if 'paragraph' in content:
        for element in content['paragraph']['elements']:
            if re.search('^([0-9]+).([0-9]+):', element['textRun']['content']):
                if document_text != '' and document_text != '\n':
                    text_title = text_title.strip().replace(' -', '-').replace('\n', ' ').replace("\xa0", "").replace(
                        "&#39;", "'").replace("&quot;", '"')
                    json_file[text_title] = document_text

                text_title = element['textRun']['content']

                document_text = ''
                to_concat = True
                continue

            if to_concat is True:
                document_text += element['textRun']['content']


for title in list(json_file.keys()):
    print(f'Title: {title}')
    print(f'Body: {json_file[title]}')

json_file = json.dumps(json_file)

with open(f'./texts/texts.json', 'w+') as outfile:
    outfile.write(json_file)
