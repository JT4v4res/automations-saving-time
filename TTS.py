import os
import re
import time
import traceback
import warnings
from typing import Dict
import pandas as pd
from openai import OpenAI
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

# Ignore DeprecationWarning
warnings.filterwarnings("ignore", category=DeprecationWarning)

SCOPES = ['https://www.googleapis.com/auth/drive.file']
error_count: int = 0


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    Sanitizes a filename to ensure it is valid for the file system.
    Args:
        filename (str): The original filename to sanitize.
        replacement (str): Character to replace invalid characters with.
    Returns:
        str: A sanitized filename that is safe for use.
    """
    invalid_chars = r'[\\/:*?"<>|\n\r]'
    sanitized = re.sub(invalid_chars, replacement, filename).rstrip(" .")
    reserved_names = {
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
        "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4",
        "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }
    if sanitized.upper() in reserved_names:
        sanitized += replacement

    return sanitized


def create_directory(base_path: str, directory_name: str) -> None:
    """
    Ensures a directory exists, logging errors if creation fails.
    Args:
        base_path (str): The base path where the directory should be created.
        directory_name (str): The name of the directory to create.
    """
    global error_count

    path = os.path.join(base_path, directory_name)

    try:
        os.makedirs(path, exist_ok=True)
    except Exception as err:
        error_count += 1
        log_error(err, directory_name)
        print(f"Error creating directory '{path}': {err}")


def log_error(error: Exception, context: str = "") -> None:
    """
    Logs errors to a file for debugging.
    Args:
        error (Exception): The exception to log.
        context (str): Additional context about the error.
    """
    with open('./error_log/error.txt', 'a+') as error_file:
        error_file.write('-' * 60 + '\n')
        if context:
            error_file.write(f"Context: {context}\n")
        error_file.write(str(error) + '\n')
        error_file.write(traceback.format_exc() + '\n')


def authenticate_google_drive() -> Credentials:
    """
    Authenticates with the Google Drive API using OAuth 2.0.
    Returns:
        Credentials: An authenticated Google API credentials object.
    """
    creds = None
    token_file = 'token.json'
    credentials_file = 'credential.json'

    try:
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    except Exception:
        pass

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    return creds


def upload_file_to_drive(file_name: str, file_path: str, mime_type: str, folder_id: str) -> str:
    """
    Uploads a file to Google Drive and returns the shareable link.
    Args:
        file_name (str): The name of the file to upload.
        file_path (str): The local path to the file.
        mime_type (str): The MIME type of the file.
        folder_id (str): The ID of the folder where the file will be uploaded.
    Returns:
        str: The shareable link to the uploaded file.
    """
    creds = authenticate_google_drive()
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {'name': file_name, 'parents': [folder_id]}

    media = MediaFileUpload(file_path, mimetype=mime_type)

    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    service.permissions().create(
        fileId=file.get('id'), body={'role': 'reader', 'type': 'anyone'}
    ).execute()

    return f"https://drive.google.com/file/d/{file.get('id')}/view?usp=sharing"


def process_excel_sheets(file_path: str) -> Dict[str, pd.DataFrame]:
    """
    Reads an Excel file and processes each sheet into a DataFrame.
    Args:
        file_path (str): The path to the Excel file.
    Returns:
        Dict[str, pd.DataFrame]: A dictionary where keys are sheet names and values are DataFrames.
    """
    excel_file = pd.ExcelFile(file_path)

    sheet_dict = {}

    column_names = [''] # insert your column names here if you want

    for sheet in excel_file.sheet_names:
        df = excel_file.parse(sheet)
        if column_names:
            df.columns = column_names
        sheet_dict[sheet] = df

    return sheet_dict


def generate_audio_for_row(client: OpenAI, row: pd.Series, output_path: str, current_sheet: str) -> str:
    """
    Generates an audio file for a single row and uploads it to Google Drive.
    Args:
        client (OpenAI): An OpenAI client instance.
        row (pd.Series): A single row from the DataFrame containing audio data.
        output_path (str): The base path where the audio file will be saved.
        current_sheet (str): The current sheet name being processed.

    Returns:
        str: The shareable link to the uploaded audio file.
    """
    slide_title = sanitize_filename(row["your_title"])
    slide_number = sanitize_filename(str(row["your_index"]))
    file_name = f"{slide_title}_{slide_number}.mp3"
    file_path = os.path.join(output_path, current_sheet, file_name)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    response = client.audio.speech.create(
        model="tts-1", voice="nova", input=row['your_text_column']
    )
    response.stream_to_file(file_path)

    return upload_file_to_drive(file_name, file_path, 'audio/mpeg', folder_ids[current_sheet])


def generate_audios(text_corpora: pd.DataFrame, output_path: str, current_sheet: str) -> pd.DataFrame:
    """
    Generates audio files for all rows in a DataFrame and uploads them to Google Drive.
    Args:
        text_corpora (pd.DataFrame): DataFrame containing text data and slide details.
        output_path (str): Path to save the generated audio files.
        current_sheet (str): Name of the current sheet being processed.
    Returns:
        pd.DataFrame: Updated DataFrame with audio file links.
    """
    client = OpenAI(api_key=os.getenv('OPEN_AI_KEY'))

    text_corpora['Audio File Link'] = text_corpora.apply(
        lambda row: generate_audio_for_row(client, row, output_path, current_sheet), axis=1
    )

    return text_corpora


if __name__ == '__main__':
    load_dotenv()

    sheets = process_excel_sheets('./text csv/your_spreadsheet.xlsx')

    folder_ids = {
        'folder_name': 'folder_id'
    }

    create_directory('.', 'error_log')
    create_directory('.', 'your_spreadsheet_name')

    start_time = time.time()

    for sheet_name, sheet_data in sheets.items():
        create_directory('./your_spreadsheet_name', sheet_name)

        sheets[sheet_name] = generate_audios(sheet_data, './your_spreadsheet_name', sheet_name)
        sheets[sheet_name].to_csv(f'./text csv/{sheet_name}.csv', index=False)

    duration = int((time.time() - start_time) / 60)

    print(f"Audio generation completed with {error_count} errors in {duration} minutes.")
