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
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_info,
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive'
                    ]
                )
            except Exception as e:
                error_msg = f"Invalid credentials format: {str(e)}"
                logger.error(error_msg)
                st.error(f"Google Sheets connection failed: {error_msg}")
                raise ValueError(error_msg)

            # Initialize service
            try:
                self.service = build('drive', 'v3', credentials=credentials)
                # Test connection
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

            # Get file metadata
            try:
                file = self.service.files().get(fileId=file_id, fields='mimeType').execute()
                mime_type = file.get('mimeType', '')
            except Exception as e:
                if "File not found" in str(e):
                    error_msg = f"File not found: {file_id}. Please verify the file ID is correct and the service account has access to it."
                    logger.error(error_msg)
                    st.error(error_msg)
                    raise ValueError(error_msg)
                raise

            if mime_type == 'application/vnd.google-apps.spreadsheet':
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            else:
                request = self.service.files().get_media(fileId=file_id)

            file_content = request.execute()
            excel_data = BytesIO(file_content)

            sheet_name = st.secrets.get("sheet_name", "Sheet1")
            logger.info(f"Reading sheet: {sheet_name}")

            try:
                df = pd.read_excel(excel_data, sheet_name=sheet_name)

                # Verify required columns exist
                required_columns = ['Train Name', 'Station', 'Time', 'Status']
                missing_columns = [col for col in required_columns if col not in df.columns]

                if missing_columns:
                    error_msg = f"Missing required columns: {', '.join(missing_columns)}"
                    logger.error(error_msg)
                    st.error(error_msg)
                    raise ValueError(error_msg)

                # Map columns to expected format
                df = df.rename(columns={
                    'Train Name': 'train_id',
                    'Station': 'station',
                    'Time': 'time_actual',
                    'Status': 'status'
                })

                # Set scheduled time same as actual time for now
                df['time_scheduled'] = df['time_actual']

                # Convert time columns to datetime
                try:
                    df['time_actual'] = pd.to_datetime(df['time_actual'], errors='coerce')
                    df['time_scheduled'] = df['time_actual']  # Using same time for both
                except Exception as e:
                    error_msg = f"Error converting time column to datetime: {str(e)}"
                    logger.error(error_msg)
                    st.error(error_msg)
                    raise ValueError(error_msg)

                # Drop rows with invalid dates
                invalid_dates = df[df['time_actual'].isna()]
                if not invalid_dates.empty:
                    logger.warning(f"Dropping {len(invalid_dates)} rows with invalid dates")
                    df = df.dropna(subset=['time_actual'])

                if df.empty:
                    error_msg = f"No valid data found in sheet '{sheet_name}'"
                    logger.error(error_msg)
                    st.error(error_msg)
                    raise ValueError(error_msg)

                logger.info(f"Successfully loaded data with {len(df)} rows")
                return df

            except Exception as e:
                error_msg = f"Error processing Excel data: {str(e)}"
                logger.error(error_msg)
                st.error(error_msg)
                raise ValueError(error_msg)

        except Exception as e:
            error_msg = f"Error accessing Google Drive file: {str(e)}"
            logger.error(error_msg)
            st.error(error_msg)
            raise Exception(error_msg)