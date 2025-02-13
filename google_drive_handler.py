import streamlit as st
from google.oauth2 import service_account
import gspread
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

            # Create credentials object
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            )

            # Initialize gspread client
            self.client = gspread.Client(auth=credentials)
            self.client.connect()  # Ensure connection is established
            logger.info("Google Sheets connection initialized successfully")

        except Exception as e:
            error_msg = f"Error initializing Google Sheets: {str(e)}"
            logger.error(error_msg)
            st.error(error_msg)
            raise

    def get_file_content(self, file_id: str) -> pd.DataFrame:
        """Download and read spreadsheet content using gspread"""
        try:
            logger.info(f"Attempting to read spreadsheet with ID: {file_id}")

            # Open the spreadsheet
            spreadsheet = self.client.open_by_key(file_id)
            worksheet = spreadsheet.sheet1  # Get the first sheet

            # Get all values including headers
            data = worksheet.get_all_values()
            if not data:
                raise ValueError("Spreadsheet is empty")

            # Convert to DataFrame
            df = pd.DataFrame(data[1:], columns=data[0])  # First row as headers

            # Clean data - handle both string and non-string columns
            for col in df.columns:
                try:
                    # Try to convert to numeric first
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    # If conversion fails, treat as string and strip whitespace
                    df[col] = df[col].astype(str).str.strip()

            logger.info(f"Successfully loaded {len(df)} rows of data")
            return df

        except gspread.exceptions.APIError as e:
            error_msg = f"Google Sheets API error: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error reading spreadsheet: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)