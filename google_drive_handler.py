import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from io import BytesIO
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleDriveHandler:
    def __init__(self):
        """Initialize Google Sheets connection using service account."""
        try:
            logger.info("Initializing Google Sheets connection...")

            # Verify required credentials exist
            required_fields = [
                'type', 'project_id', 'private_key_id', 'private_key',
                'client_email', 'client_id', 'auth_uri', 'token_uri',
                'auth_provider_x509_cert_url', 'client_x509_cert_url'
            ]

            credentials_info = {}
            missing_fields = []

            # Check each required field in st.secrets
            for field in required_fields:
                try:
                    value = st.secrets[field]
                    if not value:
                        missing_fields.append(field)
                    credentials_info[field] = value
                except KeyError:
                    missing_fields.append(field)

            if missing_fields:
                error_msg = f"Missing required Google credentials: {', '.join(missing_fields)}"
                logger.error(error_msg)
                st.error(f"Google Sheets connection failed: {error_msg}")
                raise ValueError(error_msg)

            # Add optional universe_domain
            credentials_info["universe_domain"] = st.secrets.get("universe_domain", "googleapis.com")

            # Create credentials object
            try:
                self.credentials = service_account.Credentials.from_service_account_info(
                    credentials_info,
                    scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
            except Exception as e:
                error_msg = f"Invalid credentials format: {str(e)}"
                logger.error(error_msg)
                st.error(f"Google Sheets connection failed: {error_msg}")
                raise ValueError(error_msg)

            # Initialize service
            try:
                self.service = build('drive', 'v3', credentials=self.credentials)
                # Test connection by trying to access the Drive API
                self.service.files().list(pageSize=1).execute()
                logger.info("Google Drive connection initialized successfully")
            except Exception as e:
                error_msg = f"Failed to authorize with Google: {str(e)}"
                logger.error(error_msg)
                st.error(f"Google Drive connection failed: {error_msg}")
                raise Exception(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error initializing Google Drive: {str(e)}"
            logger.error(error_msg)
            st.error(f"Google Drive connection failed: {error_msg}")
            raise Exception(error_msg)

    def get_file_content(self, file_id: str) -> pd.DataFrame:
        """Download and read Excel/Sheets content from a Google Drive file"""
        try:
            logger.info(f"Attempting to read file with ID: {file_id}")

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
            logger.info(f"Reading sheet: {sheet_name}")

            df = pd.read_excel(excel_data, sheet_name=sheet_name)

            if df.empty:
                error_msg = f"No data found in sheet '{sheet_name}'"
                logger.error(error_msg)
                st.error(error_msg)
                raise ValueError(error_msg)

            logger.info(f"Successfully loaded data with {len(df)} rows")
            return df

        except Exception as e:
            error_msg = f"Error accessing Google Drive file: {str(e)}"
            logger.error(error_msg)
            st.error(error_msg)
            raise Exception(error_msg)