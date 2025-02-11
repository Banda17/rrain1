import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from io import BytesIO
import pandas as pd
import logging
from datetime import datetime

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

    def parse_time(self, time_str):
        """Parse time string in format 'HH:MM DD-MM'"""
        try:
            if pd.isna(time_str):
                return None
            time_str = str(time_str).strip()
            # Add current year since it's not in the time string
            current_year = datetime.now().year
            # Parse time string with current year
            time_parts = time_str.split()
            if len(time_parts) != 2:
                return None
            time, date = time_parts
            hours, minutes = map(int, time.split(':'))
            day, month = map(int, date.split('-'))
            return pd.Timestamp(year=current_year, month=month, day=day, hour=hours, minute=minutes)
        except Exception as e:
            logger.warning(f"Error parsing time string '{time_str}': {str(e)}")
            return None

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
                # Read Excel file without specifying dtypes to handle all columns as strings initially
                df = pd.read_excel(excel_data, sheet_name=sheet_name)

                # Log the actual column names from the sheet
                logger.info(f"Actual columns in sheet: {list(df.columns)}")

                # Clean column names (remove leading/trailing whitespace)
                df.columns = df.columns.str.strip()

                # Verify exact required columns exist
                required_columns = [
                    'BD No', 'Sl No', 'Train Name', 'LOCO', 'Station',
                    'Status', 'Time', 'Remarks', 'FOISID'
                ]
                missing_columns = [col for col in required_columns if col not in df.columns]

                if missing_columns:
                    error_msg = f"Missing required columns: {', '.join(missing_columns)}"
                    logger.error(error_msg)
                    st.error(error_msg)
                    raise ValueError(error_msg)

                # Clean string columns
                string_columns = ['Train Name', 'LOCO', 'Station', 'Status', 'Remarks', 'FOISID']
                for col in string_columns:
                    df[col] = df[col].astype(str).str.strip()

                # Parse time column
                df['time_actual'] = df['Time'].apply(self.parse_time)
                df['time_scheduled'] = df['time_actual']  # Using same time for both

                # Map columns to expected format
                df = df.rename(columns={
                    'Train Name': 'train_id',
                    'Station': 'station',
                    'Status': 'status'
                })

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