import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from io import BytesIO
import json
import pandas as pd

class GoogleDriveHandler:
    def __init__(self):
        # Load credentials from secrets.toml
        credentials_info = {
            "type": "service_account",
            "project_id": os.getenv("project_id"),
            "private_key_id": os.getenv("private_key_id"),
            "private_key": os.getenv("private_key"),
            "client_email": os.getenv("client_email"),
            "client_id": os.getenv("client_id"),
            "auth_uri": os.getenv("auth_uri"),
            "token_uri": os.getenv("token_uri"),
            "auth_provider_x509_cert_url": os.getenv("auth_provider_x509_cert_url"),
            "client_x509_cert_url": os.getenv("client_x509_cert_url")
        }
        
        self.credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        self.service = build('drive', 'v3', credentials=self.credentials)
    
    def get_file_content(self, file_id: str) -> dict:
        """Download and read JSON content from a Google Drive file"""
        try:
            # Get the file metadata
            file = self.service.files().get(fileId=file_id).execute()
            
            # Download the file content
            request = self.service.files().get_media(fileId=file_id)
            file_content = request.execute()
            
            # Parse JSON content
            return json.loads(file_content.decode('utf-8'))
        except Exception as e:
            raise Exception(f"Error accessing Google Drive file: {str(e)}")
