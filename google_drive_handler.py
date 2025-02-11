import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from io import BytesIO
import pandas as pd

class GoogleDriveHandler:
    def __init__(self):
        # Define required fields for Google Drive authentication
        required_fields = [
            'type', 'project_id', 'private_key_id', 'private_key',
            'client_email', 'client_id', 'auth_uri', 'token_uri',
            'auth_provider_x509_cert_url', 'client_x509_cert_url'
        ]

        # Verify all required fields are present in secrets
        missing_fields = [field for field in required_fields if field not in st.secrets]
        if missing_fields:
            raise ValueError(f"Missing required Google Drive credentials: {', '.join(missing_fields)}")

        # Load credentials from streamlit secrets
        credentials_info = {
            "type": st.secrets["type"],
            "project_id": st.secrets["project_id"],
            "private_key_id": st.secrets["private_key_id"],
            "private_key": st.secrets["private_key"],
            "client_email": st.secrets["client_email"],
            "client_id": st.secrets["client_id"],
            "auth_uri": st.secrets["auth_uri"],
            "token_uri": st.secrets["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["client_x509_cert_url"],
            "universe_domain": st.secrets.get("universe_domain", "googleapis.com")
        }

        try:
            self.credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
        except Exception as e:
            raise Exception(f"Failed to initialize Google Drive service: {str(e)}")

    def get_file_content(self, file_id: str) -> pd.DataFrame:
        """Download and read Excel/Sheets content from a Google Drive file"""
        try:
            # Get the file metadata to check if it's a Google Sheets file
            file = self.service.files().get(fileId=file_id, fields='mimeType').execute()
            mime_type = file.get('mimeType', '')

            if mime_type == 'application/vnd.google-apps.spreadsheet':
                # For Google Sheets, use the export method
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            else:
                # For already uploaded Excel files
                request = self.service.files().get_media(fileId=file_id)

            file_content = request.execute()
            excel_data = BytesIO(file_content)

            # Use sheet name from secrets
            sheet_name = st.secrets.get("sheet_name", "Sheet1")
            df = pd.read_excel(excel_data, sheet_name=sheet_name)

            if df.empty:
                raise ValueError(f"No data found in sheet '{sheet_name}'")

            return df
        except Exception as e:
            raise Exception(f"Error accessing Google Drive file: {str(e)}")