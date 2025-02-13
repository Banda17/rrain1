import streamlit as st
from google.oauth2 import service_account
import gspread
import pandas as pd
import logging

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GoogleDriveHandler:
    def __init__(self):
        """Initialize Google Sheets connection using service account."""
        self.client = None
        try:
            logger.debug("Starting Google Sheets initialization...")

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
                    logger.debug(f"Found credential field: {field}")
                except KeyError:
                    missing_fields.append(field)
                    logger.error(f"Missing credential field: {field}")

            if missing_fields:
                error_msg = f"Missing required Google credentials: {', '.join(missing_fields)}"
                logger.error(error_msg)
                st.error(error_msg)
                raise ValueError(error_msg)

            # Create credentials object
            try:
                logger.debug("Creating credentials object...")
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_info,
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive'
                    ]
                )
                logger.debug("Credentials object created successfully")
            except Exception as e:
                error_msg = f"Failed to create credentials: {str(e)}"
                logger.error(error_msg)
                st.error(error_msg)
                raise ValueError(error_msg)

            # Initialize gspread client
            try:
                logger.debug("Initializing gspread client...")
                self.client = gspread.authorize(credentials)
                logger.info("Google Sheets connection initialized successfully")
            except Exception as e:
                error_msg = f"Failed to initialize gspread client: {str(e)}"
                logger.error(error_msg)
                st.error(error_msg)
                raise Exception(error_msg)

        except Exception as e:
            error_msg = f"Error initializing Google Sheets: {str(e)}"
            logger.error(error_msg)
            st.error(error_msg)
            raise

    def get_file_content(self, file_id: str) -> pd.DataFrame:
        """Download and read spreadsheet content using gspread"""
        if not self.client:
            error_msg = "Google Sheets client not initialized"
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            logger.debug(f"Attempting to read spreadsheet with ID: {file_id}")

            # Open the spreadsheet
            try:
                spreadsheet = self.client.open_by_key(file_id)
                worksheet = spreadsheet.sheet1  # Get the first sheet
                logger.debug("Successfully opened spreadsheet")
            except Exception as e:
                error_msg = f"Error accessing spreadsheet: {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            try:
                # Get all values including headers
                logger.debug("Fetching all values from sheet...")
                data = worksheet.get_all_values()
                if not data:
                    error_msg = "Spreadsheet is empty"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.debug(f"Found {len(data)} rows of data")
                logger.debug(f"Headers: {data[0]}")

                # Convert to DataFrame, keeping everything as strings
                df = pd.DataFrame(data[1:], columns=data[0])

                # Clean all string data (just strip whitespace)
                for col in df.columns:
                    df[col] = df[col].astype(str).apply(lambda x: x.strip() if isinstance(x, str) else x)

                logger.info(f"Successfully loaded {len(df)} rows of data")
                return df

            except Exception as e:
                error_msg = f"Error processing spreadsheet data: {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        except Exception as e:
            error_msg = f"Error accessing Google Sheets: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)