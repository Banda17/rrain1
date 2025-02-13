import streamlit as st
from google.oauth2 import service_account
import gspread
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, Optional

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

            # Initialize gspread client
            try:
                self.client = gspread.authorize(credentials)
                logger.info("Google Sheets connection initialized successfully")
            except Exception as e:
                error_msg = f"Failed to authorize with Google: {str(e)}"
                logger.error(error_msg)
                st.error(f"Google Sheets connection failed: {error_msg}")
                raise Exception(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error initializing Google Sheets: {str(e)}"
            logger.error(error_msg)
            st.error(f"Google Sheets connection failed: {error_msg}")
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
        """Download and read spreadsheet content using gspread"""
        try:
            logger.info(f"Attempting to read spreadsheet with ID: {file_id}")

            # Open the spreadsheet
            try:
                spreadsheet = self.client.open_by_key(file_id)
                worksheet = spreadsheet.sheet1  # Get the first sheet
            except Exception as e:
                error_msg = f"Error accessing spreadsheet: {str(e)}"
                logger.error(error_msg)
                st.error(error_msg)
                raise ValueError(error_msg)

            # Get all values including headers
            try:
                data = worksheet.get_all_values()
                if not data:
                    error_msg = "Spreadsheet is empty"
                    logger.error(error_msg)
                    st.error(error_msg)
                    raise ValueError(error_msg)

                # Convert to DataFrame without header validation
                df = pd.DataFrame(data[1:])  # Skip first row as header

                # Find Time column index (assuming it contains time values like "HH:MM DD-MM")
                time_col_idx = None
                for idx, col in enumerate(df.columns):
                    sample_values = df[col].iloc[:5].astype(str)  # Check first 5 rows
                    if any((':' in str(val) and '-' in str(val)) for val in sample_values):
                        time_col_idx = idx
                        break

                if time_col_idx is not None:
                    # Parse time data
                    df['time_actual'] = df[time_col_idx].apply(self.parse_time)
                    df['time_scheduled'] = df['time_actual']  # Using same time for both

                # Clean all string data
                for col in df.columns:
                    df[col] = df[col].astype(str).str.strip()

                if df.empty:
                    error_msg = "No valid data found after processing"
                    logger.error(error_msg)
                    st.error(error_msg)
                    raise ValueError(error_msg)

                logger.info(f"Successfully loaded {len(df)} rows of data")
                return df

            except Exception as e:
                error_msg = f"Error processing spreadsheet data: {str(e)}"
                logger.error(error_msg)
                st.error(error_msg)
                raise ValueError(error_msg)

        except Exception as e:
            error_msg = f"Error accessing Google Sheets: {str(e)}"
            logger.error(error_msg)
            st.error(error_msg)
            raise Exception(error_msg)