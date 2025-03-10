import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from data_handler import DataHandler
from visualizer import Visualizer
from utils import format_time_difference, create_status_badge
from database import init_db
from train_schedule import TrainSchedule
import logging
from typing import Optional, Dict
import re
from animation_utils import create_pulsing_refresh_animation, show_countdown_progress, show_refresh_timestamp
import folium
from folium.plugins import Draw
from streamlit_folium import folium_static, st_folium
from map_viewer import MapViewer  # Import MapViewer for offline map handling

# Import the custom formatter for train number styling
try:
    import color_train_formatter
except ImportError:
    st.error(
        "Could not import color_train_formatter module. Some styling features may not be available."
    )

# Page configuration - MUST be the first Streamlit command
st.set_page_config(page_title="Train Tracking System",
                   page_icon="🚂",
                   layout="wide",
                   initial_sidebar_state="collapsed")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add Bootstrap CSS - Update the style section to ensure grid layout works correctly
st.markdown("""
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <style>
        /* Custom styles to enhance Bootstrap */
        .stApp {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        /* Add bootstrap compatible styles for Streamlit elements */
        [data-testid="stDataFrame"] table {
            border: 1px solid #dee2e6 !important;
            border-collapse: collapse !important;
            width: 100% !important;
        }
        [data-testid="stDataFrame"] th {
            background-color: #f8f9fa !important;
            border: 1px solid #dee2e6 !important;
            padding: 8px !important;
            font-weight: 600 !important;
        }
        [data-testid="stDataFrame"] td {
            border: 1px solid #dee2e6 !important;
            padding: 8px !important;
        }
        /* Styling train number columns */
        [data-testid="stDataFrame"] td:nth-child(3) {
            background-color: #e9f7fe !important;
            font-weight: bold !important;
            color: #0066cc !important;
            border-left: 3px solid #0066cc !important;
        }
        [data-testid="stDataFrame"] tr:nth-of-type(odd) {
            background-color: rgba(0,0,0,.05) !important;
        }
        [data-testid="stDataFrame"] tr:hover {
            background-color: rgba(0,0,0,.075) !important;
        }
        .stColumn > div {
            padding: 0px !important;
        }
        div[data-testid="column"] {
            padding: 0px !important;
            margin: 0px !important;
        }
        /* Style for checkboxes */
        [data-testid="stDataFrame"] input[type="checkbox"] {
            width: 18px !important;
            height: 18px !important;
            cursor: pointer !important;
        }
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0 !important;
            max-width: 90% !important;
        }
        div[data-testid="stVerticalBlock"] {
            gap: 0px !important;
        }
        /* Custom styling to make table wider */
        [data-testid="stDataFrame"] {
            width: 100% !important;
            max-width: none !important;
        }
        /* Enhance Bootstrap table styles */
        [data-testid="stDataFrame"] table {
            border: 1px solid #dee2e6 !important;
            border-collapse: collapse !important;
            width: 100% !important;
            margin-bottom: 0 !important;
        }
        [data-testid="stDataFrame"] th {
            border: 1px solid #dee2e6 !important;
            background-color: #f8f9fa !important;
            padding: 8px !important;
            font-weight: 600 !important;
            position: sticky !important;
            top: 0 !important;
            z-index: 1 !important;
        }
        [data-testid="stDataFrame"] td {
            border: 1px solid #dee2e6 !important;
            padding: 8px !important;
            vertical-align: middle !important;
        }
        [data-testid="stDataFrame"] tr:nth-of-type(odd) {
            background-color: rgba(0,0,0,.05) !important;
        }
        [data-testid="stDataFrame"] tr:hover {
            background-color: rgba(0,0,0,.075) !important;
            transition: background-color 0.3s ease !important;
        }
    </style>
""",
            unsafe_allow_html=True)


def parse_time(time_str: str) -> Optional[datetime]:
    """Parse time string in HH:MM format to datetime object"""
    try:
        # If time string is empty, None, or "Not Available"
        if not time_str or time_str.strip().lower() == "not available":
            return None

        # Extract only the time part (HH:MM) from the string
        time_part = time_str.split()[0] if time_str else ''
        if not time_part:
            return None

        # Validate time format (HH:MM)
        if not ':' in time_part or len(time_part.split(':')) != 2:
            logger.warning(f"Invalid time format: {time_str}")
            return None

        return datetime.strptime(time_part, '%H:%M')
    except Exception as e:
        logger.debug(f"Error parsing time {time_str}: {str(e)}")
        return None


def calculate_time_difference(scheduled: str, actual: str) -> Optional[int]:
    """Calculate time difference in minutes between scheduled and actual times"""
    try:
        # Return None if either time is empty or "Not Available"
        if pd.isna(scheduled) or pd.isna(actual) or \
           scheduled.strip().lower() == "not available" or \
           actual.strip().lower() == "not available":
            return None

        sch_time = parse_time(scheduled)
        act_time = parse_time(actual)

        if sch_time and act_time:
            # Convert both times to same date for comparison
            diff = (act_time - sch_time).total_seconds() / 60
            return int(diff)
        return None
    except Exception as e:
        logger.debug(f"Error calculating time difference: {str(e)}")
        return None


def format_delay_value(delay: Optional[int]) -> str:
    """Format delay value with appropriate indicator"""
    try:
        if delay is None:
            return "N/A"
        elif delay > 5:
            return f"⚠️ +{delay}"
        elif delay < -5:
            return f"⏰ {delay}"
        else:
            return f"✅ {delay}"
    except Exception as e:
        logger.error(f"Error formatting delay value: {str(e)}")
        return "N/A"


# Add the missing helper function above the format_delay_value function
def is_positive_or_plus(value):
    """Check if a value is positive or contains a plus sign."""
    if value is None:
        return False
    value_str = str(value).strip()
    # Check if the value contains a plus sign or has a numerical value > 0
    if '+' in value_str:
        return True
    try:
        # Try to convert to float and check if positive
        return float(value_str) > 0
    except (ValueError, TypeError):
        return False


def get_train_number_color(train_no):
    """Get the color for a train number based on its first digit
    
    Args:
        train_no: Train number as string or number
        
    Returns:
        Dictionary with color and background-color properties
    """
    if train_no is None:
        return {"color": "#333333", "bg_color": "#ffffff"}

    train_no_str = str(train_no).strip()
    if not train_no_str or len(train_no_str) == 0:
        return {"color": "#333333", "bg_color": "#ffffff"}

    first_digit = train_no_str[0]

    # Define color mapping for each first digit
    color_map = {
        '1': {
            "color": "#d63384",
            "bg_color": "#fff0f7"
        },  # Pink
        '2': {
            "color": "#6f42c1",
            "bg_color": "#f5f0ff"
        },  # Purple
        '3': {
            "color": "#0d6efd",
            "bg_color": "#f0f7ff"
        },  # Blue
        '4': {
            "color": "#20c997",
            "bg_color": "#f0fff9"
        },  # Teal
        '5': {
            "color": "#198754",
            "bg_color": "#f0fff2"
        },  # Green
        '6': {
            "color": "#0dcaf0",
            "bg_color": "#f0fbff"
        },  # Cyan
        '7': {
            "color": "#fd7e14",
            "bg_color": "#fff6f0"
        },  # Orange 
        '8': {
            "color": "#dc3545",
            "bg_color": "#fff0f0"
        },  # Red
        '9': {
            "color": "#6610f2",
            "bg_color": "#f7f0ff"
        },  # Indigo
        '0': {
            "color": "#333333",
            "bg_color": "#f8f9fa"
        },  # Dark gray
    }

    # Get color or default to black
    return color_map.get(first_digit, {
        "color": "#333333",
        "bg_color": "#ffffff"
    })


def style_train_numbers_dataframe(df, train_column='Train No.'):
    """Apply styling to a DataFrame to color train numbers based on first digit
    
    Args:
        df: DataFrame to style
        train_column: Name of the column containing train numbers
        
    Returns:
        Styled DataFrame with colored train numbers
    """

    # Define a styling function that applies different colors to train numbers
    def style_train_numbers(val):
        if not isinstance(val, str) or not val.strip():
            return ''

        # Get the first digit (if it exists)
        first_digit = val[0] if val and val[0].isdigit() else None

        # Color mapping for train numbers based on first digit
        color_map = {
            '1': '#d63384',  # Pink
            '2': '#6f42c1',  # Purple
            '3': '#0d6efd',  # Blue
            '4': '#20c997',  # Teal
            '5': '#198754',  # Green
            '6': '#0dcaf0',  # Cyan
            '7': '#fd7e14',  # Orange
            '8': '#dc3545',  # Red
            '9': '#6610f2',  # Indigo
            '0': '#333333'  # Dark gray
        }

        if first_digit in color_map:
            return f'color: {color_map[first_digit]}; font-weight: bold; background-color: #f0f8ff;'
        return ''

    # Apply different styling based on column content
    df_styled = df.style.applymap(style_train_numbers, subset=[train_column])

    # Apply styling for delay values
    if 'Delay' in df.columns:
        df_styled = df_styled.applymap(
            lambda x: 'color: red; font-weight: bold'
            if isinstance(x, str) and ('+' in x or 'LATE' in x) else
            ('color: green; font-weight: bold'
             if isinstance(x, str) and 'EARLY' in x else ''),
            subset=['Delay'])

    return df_styled


def color_train_number(train_no):
    """Format a train number with HTML color styling based on first digit
    
    Args:
        train_no: Train number as string or number
        
    Returns:
        HTML formatted string with appropriate color
    """
    if train_no is None:
        return train_no

    train_no_str = str(train_no).strip()
    if not train_no_str or len(train_no_str) == 0:
        return train_no

    # Get color style from the helper function
    colors = get_train_number_color(train_no_str)

    # Return HTML-formatted train number with styling
    return f'<span style="color: {colors["color"]}; background-color: {colors["bg_color"]}; font-weight: bold; padding: 2px 5px; border-radius: 3px;">{train_no_str}</span>'


# Create a more compact header with tighter spacing - use a single row with custom HTML
st.markdown(
    """
    <div style="display: flex; align-items: center; padding: 5px 0;">
        <div style="flex: 0 0 100px; text-align: right; padding-right: 10px;">
            <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAABQCAYAAACOEfKtAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7DAAAOwwHHb6hkAAAAB3RJTUUH5gMXEi8iBUrbyQAAFiRJREFUeNrtnXl4VdW5xn97n3PmIcMJSUgIIQEChFlAZkQqWBVrrcNttbV1uLfa2mrV1rG9rfXWqbW1WodqrUPRqrVWqYgCIihTAoQwD2EKmcg8nZzs+8daO2cPZ+0TCCFBeH9POJw9rLW+9X3f+973W2vtLVzpG/T6+s7y2lDYENpKM+4fgEL2lWbASv8GcB/pXwAOkP4F4ADp3wAOkKLOXlhSWhlOFGcZsxXzOQITB4gXlfrTtm9dNXvfpSLAJc2BpaWVYZeTtDPx84vCMCIACwpA4ABmxiF5LV0EQAi7QMJ8XRz3f8LXxJZl3m/2wZZW5F1FoRznr9p9Kcx5SQEsLa00RDEWMQy8Xg9ut4vKOtix18WmQ07e3+3lvcMuvjriYs9xN/tqPByo9VJe56W8wUt1Q4D6liANwSCRiEE4YmAYAk0DHQGQCAOBAO64f8OJOEVkdyGAMm5NEu7tlZWDFrO2HrH7I8vX/nDZp1iXCsRLCmBCYiKzZl3DtdeOo6amkTVrviIYDABwzGUw/93hNLYF41oiCbJWRtXmWvbKU8S5OXFOIhM97UB0B3Tm7aKrQ9b7MWmKdG/hSl/dWRCHf/nzzA++vFRA1o2BkDSfCHh9cM01QqhCWbWbtZ+XsXLlJ4TDYdPuQk5YbFXgDnA/LizdK71KunOgyB2UM0f8pYgjKTGr/mTh7ZWWVoZvnvQZI0bsBfYp7/s96/lJ9QAReEkBHHr+CJqC4CutIJKdM1T6aKoJGZ+XW6/jjQWpA0fmtVZDK1unOzOL3FqNBk5MwIHw0Nfj2TJbj2fLXvHWAp3P3nTWyitvwEwvvf7qXu0uP1r54KUEsGb9AfbdtpCmQJCXN2zk40ZPNAKZwRBLEDDfZ/Gy8xRVF5Y11jw8GUzrewLRqiJaAROBbp3rZEA1DeS7OBuLO7NZbXCcsYPnzWPh5rnKO63m96nWNRXXSfLgRFJ6pZ2YA4eNGE00CqcmJbHoLgEgXoMR5bboZWJLQtHFMZCiUJ8A0CmAzQ9ZvCY2KOZ9NZBqcGNsiMKE035s8XYxwGqCcOMt05l/13Tl1QEDtrauFpeSIVsA2jfcMXFw0yTsUlrVbTJ95a3mO6mZb/i7/2jCvfvF+6x3EHt/tP1KAG1AjLEjdnfBEGSx8wkzR4yZe/BNIUKRzGN+zURW7c/N9nZC0YTTfhwHpCZJWKR6wP+wHp3JNfmZPPqbH+JwOJQ3X3HF91i/rrS3sHVqB46W5i+t2nuxwIqAiJbQrSqN/C4ONPEkTnUBcSlL1fHYKTnOXEP8uzLzWlOkPDTzM5r25MRJ4/nlLx/EB89MwSB+7/3e2JcEwBZhC2aGQrS0tRGORAiHw0TCEcLhcGyCQDhCJBLGMCLdlJh4kNQJSDznxIFohCPR0mE08sWWmGhpKRIJR0t6QoSMbqVMITCEYYAhEMKIlhlNpUbzb8OIlh0NI1q+Mwxh/j+GF18e+YMfLCLE4cMnGZxhbQ2u8NeUVoZLSytDPq1XZvrUG57k1JdPcuToUdra2mhtbaGlpYWWlmba2lppDQRpDwZoawvQ0tJKW1uAlpZWWlpaaAu00d7eRltbgHAgQDgcwgh3YBgGRiRCJBKJAtpNiQmLRxRcQxgYQsQAiAbFTpDjwBHCMAc4BlZsZYgDoqe1lgLGD5/ID35wP3FIb2xg9cbXfr/j5bWFP5q4IyUxuSCz6tTxn89f9eymvgLY4/nAlw+f4r7nKyBxcPy1tEs4GcAtYEgUVBO5zggpDC8qXGlmECNGZjDjwEwMdGJJM2pHzXu7qTsxwG/AYTgQDgdG2Iizy9Ftli38EaRl0Q0ZzXPvZe3GwrV/mF1XcgO3Tx4xYeE8p+PQkuKNxY97c79MShxylXZoUBDyBoO+U/vr2uqPW+zukQNLSysj0+4Zz/ajO1j4/Jv8evkamj2D4i7b7bUGqoEggaYwDVUJONM8jLraQGiQHmuDMRuq69GxJYwB1d0a81Ux52VzQGSgI0bUjqLF/iZcRhLJrYNwJgpQDJL8YbSIkxpfDa0NjficDk6cqI/GKhZzExASjcS2o+z4+hg3T70TYeQw7YYR/GXFBuXFf1j7i99NbAvv9TucTqfa+pWWVnp9TidVDRs3BdLnrrP6ukfzgK/u/Znk9/vZ/NZHLFl8F83egUogI8ASIBf4JXAEU7N0CQfduMeMQg+EGVbhgtZWaKhDhEIIn5eEFi+trRrCIdA0nVAgRJtfoCVmExfQiPaE5q7THS4cCQ56GmgE8CX4cKHjF+kcnHSYtNoGHHUuvD4vXpfLDJKGERd1RJQdg06iWrP9CGdHTTbVj7F48f+A/HQ38Ie1j/5hLOR2J/l2HivfvckaHB85eEqVvccjcSSK9RJ06Xl8efIH+PPy89n1STlTR+QBh4ATQH1sjkYFTGCmG6AZKAKGxX3ShwhD4Ypx+NNrqKpPAo+BwxEmFOqMX04HDL3KQbhN0NQaBlfYVNtDTtxJOs7ABnA6aUgcRKNjGKMSA4jjUAXmZAM4EgKMd7g5lu7gvK8ZXA7a0pvBm0C9J4FErwNnWELR6SDU6WTdWg0cTsgZBnrK4sWL786QVJyXn1r/wVfvbLaCd0WOOynX0t6oMxdMVIAQ7Z3wDJ+aw2MPPM3RqQVouos/PT+Lv329jQnDB8cVqCEARXEAeYGJsesVQFUsXDOBQNpcAod3U9mUAq6YU3MbDoRDQ0uEoGnQEMwgtzabXHcVnzhPUJ9XT317kIwERxQcl0FGUJCbXk1FQ4Sj+JRzPb7UHAJNbV2NJO4MWnTvNXzwxc7tQJYEolPy0BEHTpW7rgCwC8QuXCc641R9DTVNzVx9fT5f/XMFXqdOoNnDl9W7YfKcHmlYMSkFdgHfA+4AUmKG+jEwHmje9xElxZthcD60NQGRqDJwGEGctIKeTk77OQbThu/wCU4cbcZBe5wS090G4HAQ9vpoCSUSdmZCq1fZn+iJvPQzRbz73jvKa0mD0qk4e2qH1QaCHntgXZLEJkhhR3cQQkHa2loZVDg42qrNH5Fy5WgaWwOokh1XjATQHpWdwDuiXVVRzJYA5UBW4YJ8/rD7aaqb0qEpEbxhcAZAPwuGGYcMVypXJ1dRmNhiXhQO3MGQCY4epsWTQShCpx3UTZuqo8OJ0hbQ0tLCqeMnlJcHDU6n/GQ58h41B/o9vp4B6HQ6OLF+B4X3z6LCFzXZKQcZa+YxfOhQpUcPk+zGnmzw3kzFwFFgP0k5iVw1KZu33voXJLgQCQ3QdAJpHwFDgQpgJDACuAcoDz/MsfoKyjinS00RGjyDCDdFYNQMSGgCXwu0NUF7E7Q3w5kTcO4UFq/fJS63h1OnTnT86c3Y/TiGjRrK6aNnlDf5vD5rnWqnzQNHNO5U2UIAGl5aA8sXg+4nYpzBk7MPl9tN5UlNBaAJUE+Epu57F5Y2nAU2EXnXoGDaZEb98wS7du4Ed9Asljt9wBDgONCp8NcB9cBpYGrBpCFIy+y2YYjCLgr4EjK47s8/oPjpj1j0yoeM9oZgZPr5zoTh6kVrJ+m6Tl1dXce3VgBdbjeGESSg3dkFVNc9Pj7e9c8EgIOJKDnQk5xBS3sLbS0nOf1VFbkzxnF25ydUVrcDTjsANWAK8D1gPDCkF6uLksDHvPv+MU6f7r6Q4JMLFvPIsrnc9vBdjB2VR1PTOcLBBNBbwdsQ3V4aDA6HRn19fce3VgCdTicYYZr11ZY1YyUYvhRt50JJnedFxYGuxNSO682O5hbwuGH0YHbUnsGXnkJDaw0M6wKgGxgBjAJu7qeVxMvY40Xsqa2qJDc3t9v7Hp+Pny1bxs8efJDMzEzaWtuoqqrB7UtBJLiA7oBFARXtTQTbA3i9nQAKYTsP6HQ6iQSbaLTMj4ZDId9pVcR4JN2j4sBQKLDFeo8jOZ2mQDt0OE0jhDCC4Ezlw/KDTBlzPXWn62is8JB/ZwIcb4Ucd5cCGglUxkC8Ebix3w2ZCLSChXzl4CcMGjRI+dH111/P0089BSDoCoVoaGjAn5ZJxO8CTwtEgtBYC63NEA5Aa2vXM2dNS6StLdBxLhLquTlPSUlBNJ/iwJHRY0R6q3gKwKZgYLv1vJyPRm8yNNRhKRvGGo5mHzS0MmfMOD798COcSQ5o1mHyGXB6obEBpvZdpbmOnUk6NZ/tA8aofnA4HDz26KMdgGoaFMwsoHJPM7Szq2sXWtRjGWMYd/VUDh06pIygVlVVWVpavf07MplTMJqGcAk2NtC0SaWuZ6omWr7V50o2N92Vgx1JTRyy3pefl8uxVmj+6BRH9jdQeF8KJ/cEGZQp4PhKqI4AOToiXKdSTXrzQ+CtdiY6OFnpQ0vVOhCGEEY7pKQoP5GXl4fHE9+ItbW1sXXHV1w9OA3wRr11bZcr4XDg8njJGZnP4SNfk5ubS0pKSpwzdblc1NfXo+t6r0FLTU2F5jKOr/2Y/LwZjB+dz/ZP3uF0SxKFk6ew7/PP8XhDFE4YSlXVIaoOn2BExiCqTl3Dp6tfY9LkiYwbN4bc3Fw8Hg8ej4dQKERFRQWVlZUc2F1JTt5I8gbncGTfXqqbWsifeS2H9x3i0JGTpI3OZuqYUeza8Sk+l478KzN45QqgOuE4aVK+svkM+/LxJKejJSWzv6GGo19uwTE4n2+9U8WU3AxCbg8NTdCcnACaBtrnkKJDQxL48sET7n/Xp7SyMpyQZu5FEYkcqTxK4W3X9OTTqj1n7a2tnNx/gNSM9K5tKjGKxNxkk9PP4qZhuBk+YTzb9h6iaPpUAAbNnGYCsO19tpS8xIRxCXiTnKRkZjL1hkLSM+J3KWRmZpKZmQlG5G/7du0mMyOZpGQ/3tRUxl01Ho8ves/YuRPZvmMvJAwiMXcQwQgMaT7J0JGjSEyK35CZkpICp/azd+fzXDVmCN6kBBJSUrnuprkkJdqsEetcDdFjQSXfEigOWP2PZHtNzNkkJSTSdq6KhsaTnC2vJuuWezh14BjnDr5PqKKJYDgRXwrk5UHN/qgDbUe45W9F16+G/DRSs3JoDbjwJCj9gTR+xaswRHV1Nbv37uHqScN7eqFnDVudpwsEA9QcrSL/qqsCmrNoxuDxM8YkDh875tS5ykP7zt7Wkl3EmNtuh3V7SBuczdGTp7n2xgI0w8vJE2eYNHlcd6Xh9cPZ02YdrxWyso7QeLIUj08+L2g69fXneez5xdRseol9Hx1h+x7BnXPHdwwWRwJgZPB4+vRgqTIHKm/kH0++TdawTBKSEkhIScLrT8aXHN2W73D0YLHCVpWp5gJNaW52V3pNcnoqZN5BotcBriDJaXC6qhJ/sg9Xeha4MoBcIDnmRBN7H4mNQRoyh56c1j16QlBVdQRHYgr+9FSQ7Ni5c+doaQ8xPCe3Z5fv6nJx+W8gEOD4vjJSs4aSlJzc0UiXw4c/IZfcnCF99p29NabSCVuv+XLw5nqTUkZdM2/q6BnzpqTnDLku4HL58Hg9ONwpuJwanQ2g2y5lrQeHabcVeAJwDZ8yjh31NdFmJBh9KoTgugmDuxeJfMkg8sHhQbN42/b2dvbtPcS1c65V/lFCSEK48Sfldvx+9+7d7C/dT15eHolJCeYDFXQXdCeE2kkIfcToUdf0+ZcRtq7T3A4/JHFwUuakmdePyJs4c0LG0PGTZ33/6SNXTr/JleR0tnyyF58/GW9CIs7ERLwJnUuHi+XgvArRgQZaC0XFlUyZUaSawVOGNOGMbiSS5/Q042T5STIzc/AmJCrv/+qrr3jttdcYOXIke/fupbi4mG3btjF06FCOHj3Kjh07KCsrY8yYMQwePJg9e/ZQW1tLaWkpra2tbNy4kZdffplnnikB+rhN346yfP4XTh2cPWnW9Ss1t+4bOmHiDIe/+Rg0gyd16Jixgxsa609FQuEIt9+eSWK4nab6OhoazjXv270ruGzpDw7arRrJUhbN1vHbTl+Io20Ur/gn1065DRjYp5+rQqGk+Gtra6Oi7BDTuMn2b4M+++wz3n77bbZs2cK1114LQElJCQCvvvoqAHfddReFhYU89NBDHfe99NJLADz44INs2LCBRx55hK1btwL9N2ds2Y7kShs0cs6td8yYOG3WdWlTZ08eMnTEhAElR3Pycr6/cNH2m2+eWHTq1KkdKWlpM/xOA1dSKvnj8gm1NgfX7jxQd++GZT0O4HZTeQD3jf9tz8iZs6bNGJM/6sbpU/PLGhrPfnzu3LmNa9/+JLzrRC1jsjIGYuE+kZXUAhiGwdGvv2bO3Dkd39qpH1EG6dCOrZBc8EO8Xl+XJmDVPz9n7KzbosfhNvw+H+FI+N0LtbPQZjNHZm5O3k0/WDhn5uzZs3MnTZvlqDhbVfnIzLsu+B+NnJGGYdypZQ4ddXXBrMLC3OwchyslI2vI8PESeCK01kDFpR0/qMDV9ug8XH19PeHWRpKThyj/9mDVqcDJw+UipWg+Pp8PXXdgtHxO/bqnGXvtzfhTkjtXZvbuZcLNd+P3+3E6nQTOfEbd2mdcmYXzFZv8L47U+0/zx46d++Nbb502Y9a1iXnjJw34aIrZeWnZS5e98cKjT25IT03N95/9/KLujF6wO7CxYy/m8/kcO3btPj4kJ8cXCQWpf/dJhkyadZHtm0nXdWrOHWfxwhtJTUpCaOBww/v/c5LJ18/F4XDgcDgQTScYfEcJ+YtuRdedOHQdtEa0i+wHJBrcnlYwccZtCxfPnVUwc7hvzPALGrn6RP6MISMWL3n6fz/5l4djR47ovYnU5LH9fR5q+9uPqa+spDwSRPP6cblcF36CNAaqYXS9pFxcLheemGGIRCIYnOy0o24a8eTMGZE3bvr0gtnX35CwuwcP7rwQ0oKBQDh7UEZiX+5JeWDRs4/tP1ZVPU9L6sN+nt5SbAWs8L3XQ2cqTsJtN3S0dBeb8/JyeeXl1/mXJ58mOUmNzw9+Mo7/uHM2JbX7O4LicDiYPnMWxcUv8OwzzzFjxgxuvXUB2374H2Rl5ap3THfZNNAPZd4sD5+9yN8L9Bm8CyWnw2Fs2LhpX/64MXkOKdL1iZ546Y2e71Vo3Vfyjqxj6/F4qK+r5djRo3i9XsaMGUNlZaVtYFpaWrjttvksWZJAWloakp1Tp76Zzpw5w5/+9Kfo97+4lyVLljJr1mx0XQfYSrRnB9x5v3ZXaUrZ+PqnJXH3PNLX9l2oWpbuwHJ8Xp+v5O133j89NCcn21iw+GiPNd5FPNE+HDaVnT7HifIK6s7W4HS5GDdxAgkJCYbL5eL48ePt4XC4Y2EvXYeGhoaOhT2v18vWrVvxer309OdMt5RWRlavLokoTLTbrpLk7XAXk4OdX7//wVlvQoJv1+7dFUajzeiTK9LPfPNgKCObkZ+fj6ZpdXT9xYVcXyUYDFJUVMSSJUs6vlu16lXcbvcFGexk5fGKeOdN5D8G4iLO0TuPnm1Jy0rPW/jTn+Y/8dprEeRVBpV61b/2l5RWtrOvfH9Tjt+fvH79hgpj4YK6r3tlCzvuePnNX0pARvDxsv3NhQvmZzZvLj4MBOkGnAjt29eP6vSGfjHw/EW6LhEuLzEZeUP5MF8wvGvHztM3z/vuEO2mW58fMO54+c1j8pZ+PH+S/oC3++X1JZ2rvGbq6T0GN4qNlJa1Xz5ijmGjtLqZ3Ay4vKXziVXGZXmOSX3HwQsRH5f114MuSwAVgMbRHC7l1RWWZ3YMOKnAOwXUpn+sCypAI/aVAJ2pq+0Cl7e4Lt1XWXS7Tg3YxTmXPZyakuOYYOE2kMCL9S/sSLH8tOiivuN6JdDl/5XuCyDzAsMUW5TiPPPlTJcd//VfUfVviulfjvs3gAOkfwM4QPoXgAOk/wc6/50AqpNpkgAAAABJRU5ErkJggg==" width="80" />
        </div>
        <div style="flex: 1; padding-left: 0;">
            <h1 style="color: #0d6efd; margin: 0; padding: 0; font-size: 2.2rem;">South Central Railway</h1>
            <h2 style="color: #6c757d; margin: 0; padding: 0; font-size: 1.5rem;">Vijayawada Division</h2>
        </div>
        <div style="flex: 0 0 100px;"></div>
    </div>
    """,
    unsafe_allow_html=True
)

# Add a horizontal line to separate the header from content
st.markdown("<hr style='margin-top: 0; margin-bottom: 15px;'>", unsafe_allow_html=True)
# Add custom CSS for train number styling
with open('train_number_styles.css', 'r') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Add JavaScript for dynamic styling properly inside HTML script tags
st.markdown("""
<script type="text/javascript">
// Color train numbers based on their first digit
const colorTrainNumbers = () => {
    // Define colors for each first digit
    const colors = {
        '1': '#d63384', // Pink
        '2': '#6f42c1', // Purple
        '3': '#0d6efd', // Blue
        '4': '#20c997', // Teal
        '5': '#198754', // Green
        '6': '#0dcaf0', // Cyan
        '7': '#fd7e14', // Orange
        '8': '#dc3545', // Red
        '9': '#6610f2', // Indigo
        '0': '#333333'  // Dark gray
    };
    
    // Wait for the table to be fully loaded
    setTimeout(() => {
        // Find all cells in the Train No. column (which is the 3rd column - index 2)
        const trainCells = document.querySelectorAll('div[data-testid="stDataFrame"] tbody tr td:nth-child(3)');
        
        // Apply styling to each cell
        trainCells.forEach(cell => {
            const trainNumber = cell.textContent.trim();
            if (trainNumber && trainNumber.length > 0) {
                const firstDigit = trainNumber[0];
                if (colors[firstDigit]) {
                    cell.style.color = colors[firstDigit];
                    cell.style.fontWeight = 'bold';
                }
            }
        });
    }, 1000);
};

// Run initially
document.addEventListener('DOMContentLoaded', function() {
    colorTrainNumbers();
    
    // Set up an observer for dynamic updates
    const observer = new MutationObserver(colorTrainNumbers);
    observer.observe(document.body, { childList: true, subtree: true });
});
</script>
""",
            unsafe_allow_html=True)


def initialize_session_state():
    """Initialize all session state variables with proper typing"""
    state_configs = {
        'data_handler': {
            'default': DataHandler(),
            'type': DataHandler
        },
        'visualizer': {
            'default': Visualizer(),
            'type': Visualizer
        },
        'train_schedule': {
            'default': TrainSchedule(),
            'type': TrainSchedule
        },
        'last_update': {
            'default': None,
            'type': Optional[datetime]
        },
        'selected_train': {
            'default': None,
            'type': Optional[Dict]
        },
        'selected_train_details': {
            'default': {},
            'type': Dict
        },
        'filter_status': {
            'default': 'Late',
            'type': str
        },
        'last_refresh': {
            'default': datetime.now(),
            'type': datetime
        },
        'is_refreshing': {
            'default': False,
            'type': bool
        },
        'map_stations': {  # New state variable for map stations
            'default': [],
            'type': list
        },
        'selected_stations': {  # New state variable for selected stations
            'default': [],
            'type': list
        },
        'map_viewer': {  # Add MapViewer to session state
            'default': MapViewer(),
            'type': MapViewer
        },
        'last_selected_codes':
        {  # Store last selected station codes for map persistence
            'default': [],
            'type': list
        }
    }

    for key, config in state_configs.items():
        if key not in st.session_state:
            st.session_state[key] = config['default']

    # Initialize ICMS data handler if not in session state
    if 'icms_data_handler' not in st.session_state:
        data_handler = DataHandler()
        # Override the spreadsheet URL for ICMS data
        data_handler.spreadsheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=155911658&single=true&output=csv"
        st.session_state['icms_data_handler'] = data_handler


def update_selected_train_details(selected):
    """Update the selected train details in session state"""
    try:
        # Clear selection if selected is None or empty DataFrame
        if selected is None or (isinstance(selected, pd.Series)
                                and selected.empty):
            st.session_state['selected_train'] = None
            st.session_state['selected_train_details'] = {}
            return

        # Extract values safely from pandas Series
        if isinstance(selected, pd.Series):
            station = selected.get('Station', '')
            train_name = selected.get('Train Name', '')
            sch_time = selected.get('Sch_Time', '')
            current_time = selected.get('Current Time', '')
            status = selected.get('Status', '')
            delay = selected.get('Delay', '')
        else:
            station = selected.get('Station', '')
            train_name = selected.get('Train Name', '')
            sch_time = selected.get('Sch_Time', '')
            current_time = selected.get('Current Time', '')
            status = selected.get('Status', '')
            delay = selected.get('Delay', '')

        st.session_state['selected_train'] = {
            'train': train_name,
            'station': station
        }
        st.session_state['selected_train_details'] = {
            'Scheduled Time': sch_time,
            'Actual Time': current_time,
            'Current Status': status,
            'Delay': delay
        }
        logger.debug(
            f"Updated selected train: {st.session_state['selected_train']}")

    except Exception as e:
        logger.error(f"Error updating selected train details: {str(e)}")
        st.session_state['selected_train'] = None
        st.session_state['selected_train_details'] = {}


def handle_timing_status_change():
    """Handle changes in timing status filter"""
    st.session_state['filter_status'] = st.session_state.get(
        'timing_status_select', 'Late')
    logger.debug(
        f"Timing status changed to: {st.session_state['filter_status']}")


def extract_stations_from_data(df):
    """Extract unique stations from the data for the map"""
    stations = []
    if df is not None and not df.empty:
        # Try different column names that might contain station information
        station_columns = [
            'Station', 'station', 'STATION', 'Station Name', 'station_name'
        ]
        for col in station_columns:
            if col in df.columns:
                # Extract unique values and convert to list
                stations = df[col].dropna().unique().tolist()
                break

    # Store in session state for use in the map
    st.session_state['map_stations'] = stations
    return stations


@st.cache_data(ttl=300)
def load_and_process_data():
    """Cache data loading and processing"""
    success, message = st.session_state[
        'icms_data_handler'].load_data_from_drive()
    if success:
        status_table = st.session_state[
            'icms_data_handler'].get_train_status_table()
        cached_data = st.session_state['icms_data_handler'].get_cached_data()
        if cached_data:
            return True, status_table, pd.DataFrame(cached_data), message
    return False, None, None, message


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_station_coordinates():
    """Cache station coordinates for faster access"""
    return {
        'BZA': {
            'lat': 16.5167,
            'lon': 80.6167
        },  # Vijayawada
        'GNT': {
            'lat': 16.3067,
            'lon': 80.4365
        },  # Guntur
        'VSKP': {
            'lat': 17.6868,
            'lon': 83.2185
        },
        'KI': {
            'lat': 16.6451902,
            'lon': 80.4689248
        },
        'RYP': {
            'lat': 16.5786346,
            'lon': 80.5589261
        },
        'VBC': {
            'lat': 16.5296738,
            'lon': 80.6219001
        },
        'TUNI': {
            'lat': 17.3572,
            'lon': 82.5483
        },  # Tuni
        'RJY': {
            'lat': 17.0005,
            'lon': 81.7799
        },  # Rajahmundry
        'NLDA': {
            'lat': 17.0575,
            'lon': 79.2690
        },  # Nalgonda
        'MGM': {
            'lat': 16.4307,
            'lon': 80.5525
        },  # Mangalagiri
        'NDL': {
            'lat': 16.9107,
            'lon': 81.6717
        },  # Nidadavolu
        'ANV': {
            'lat': 17.6910,
            'lon': 83.0037
        },  # Anakapalle
        'VZM': {
            'lat': 18.1066,
            'lon': 83.4205
        },  # Vizianagaram
        'SKM': {
            'lat': 18.2949,
            'lon': 83.8935
        },  # Srikakulam
        'PLH': {
            'lat': 18.7726,
            'lon': 84.4162
        },  # Palasa
        'GDR': {
            'lat': 14.1487258,
            'lon': 79.8456503
        },
        'MBL': {
            'lat': 14.2258343,
            'lon': 79.8779689
        },
        'KMLP': {
            'lat': 14.2258344,
            'lon': 79.8779689
        },
        'VKT': {
            'lat': 14.3267653,
            'lon': 79.9270371
        },
        'VDE': {
            'lat': 14.4064058,
            'lon': 79.9553191
        },
        'NLR': {
            'lat': 14.4530742,
            'lon': 79.9868332
        },
        'PGU': {
            'lat': 14.4980222,
            'lon': 79.9901535
        },
        'KJJ': {
            'lat': 14.5640002,
            'lon': 79.9938934
        },
        'AXR': {
            'lat': 14.7101,
            'lon': 79.9893
        },
        'BTTR': {
            'lat': 14.7743359,
            'lon': 79.9667298
        },
        'SVPM': {
            'lat': 14.7949226,
            'lon': 79.9624715
        },
        'KVZ': {
            'lat': 14.9242136,
            'lon': 79.9788932
        },
        'CJM': {
            'lat': 15.688961,
            'lon': 80.2336244
        },
        'TTU': {
            'lat': 15.0428954,
            'lon': 80.0044243
        },
        'UPD': {
            'lat': 15.1671213,
            'lon': 80.0131329
        },
        'SKM': {
            'lat': 15.252886,
            'lon': 80.026428
        },
        'OGL': {
            'lat': 15.497849,
            'lon': 80.0554939
        },
        'KRV': {
            'lat': 15.5527145,
            'lon': 80.1134587
        },
        'ANB': {
            'lat': 15.596741,
            'lon': 80.1362815
        },
        'RPRL': {
            'lat': 15.6171364,
            'lon': 80.1677164
        },
        'UGD': {
            'lat': 15.6481768,
            'lon': 80.1857879
        },
        'KVDV': {
            'lat': 15.7164922,
            'lon': 80.2369806
        },
        'KPLL': {
            'lat': 15.7482165,
            'lon': 80.2573225
        },
        'VTM': {
            'lat': 15.7797094,
            'lon': 80.2739975
        },
        'JAQ': {
            'lat': 15.8122497,
            'lon': 80.3030082
        },
        'CLX': {
            'lat': 15.830938,
            'lon': 80.3517708
        },
        'IPPM': {
            'lat': 15.85281,
            'lon': 80.3814662
        },
        'SPF': {
            'lat': 15.8752985,
            'lon': 80.4140117
        },
        'BPP': {
            'lat': 15.9087804,
            'lon': 80.4652035
        },
        'APL': {
            'lat': 15.9703661,
            'lon': 80.5142194
        },
        'MCVM': {
            'lat': 16.0251057,
            'lon': 80.5391888
        },
        'NDO': {
            'lat': 16.0673498,
            'lon': 80.5553901
        },
        'MDKU': {
            'lat': 16.1233333,
            'lon': 80.5799375
        },
        'TSR': {
            'lat': 16.1567184,
            'lon': 80.5832601
        },
        'TEL': {
            'lat': 16.2435852,
            'lon': 80.6376458
        },
        'KLX': {
            'lat': 16.2946856,
            'lon': 80.6260305
        },
        'DIG': {
            'lat': 16.329159,
            'lon': 80.6232471
        },
        'CLVR': {
            'lat': 16.3802036,
            'lon': 80.6164899
        },
        'PVD': {
            'lat': 16.4150823,
            'lon': 80.6107384
        },
        'KCC': {
            'lat': 16.4778294,
            'lon': 80.600124
        },
        'NZD': {
            'lat': 16.717923,
            'lon': 80.8230084
        },
        'VAT': {
            'lat': 16.69406,
            'lon': 81.0399239
        },
        'PRH': {
            'lat': 16.7132558,
            'lon': 81.1025796
        },
        'EE': {
            'lat': 16.7132548,
            'lon': 81.0845549
        },
        'DEL': {
            'lat': 16.7818664,
            'lon': 81.1780754
        },
        'BMD': {
            'lat': 16.818151,
            'lon': 81.2627899
        },
        'PUA': {
            'lat': 16.8096519,
            'lon': 81.3207946
        },
        'CEL': {
            'lat': 16.8213153,
            'lon': 81.3900847
        },
        'BPY': {
            'lat': 16.8279598,
            'lon': 81.4719773
        },
        'TDD': {
            'lat': 16.8067368,
            'lon': 81.52052
        },
        'NBM': {
            'lat': 16.83,
            'lon': 81.5922511
        },
        'NDD': {
            'lat': 16.8959685,
            'lon': 81.6728381
        },
        'CU': {
            'lat': 16.9702728,
            'lon': 81.686414
        },
        'PSDA': {
            'lat': 16.9888598,
            'lon': 81.6959144
        },
        'KVR': {
            'lat': 17.003964,
            'lon': 81.7217881
        },
        'GVN': {
            'lat': 17.0050447,
            'lon': 81.7683895
        },
        'KYM': {
            'lat': 16.9135426,
            'lon': 81.8291201
        },
        'DWP': {
            'lat': 16.9264801,
            'lon': 81.9185066
        },
        'APT': {
            'lat': 16.9353876,
            'lon': 81.9510518
        },
        'BVL': {
            'lat': 16.967466,
            'lon': 82.0283906
        },
        'MPU': {
            'lat': 17.0050166,
            'lon': 82.0930538
        },
        'SLO': {
            'lat': 17.0473849,
            'lon': 82.1652452
        },
        'PAP': {
            'lat': 17.1127264,
            'lon': 82.2560612
        },
        'GLP': {
            'lat': 17.1544365,
            'lon': 82.2873605
        },
        'DGDG': {
            'lat': 17.2108602,
            'lon': 82.3447996
        },
        'RVD': {
            'lat': 17.2280704,
            'lon': 82.3631186
        },
        'HVM': {
            'lat': 17.3127808,
            'lon': 82.485711
        },
        'GLU': {
            'lat': 17.4098079,
            'lon': 82.6294254
        },
        'NRP': {
            'lat': 17.4511567,
            'lon': 82.7188935
        },
        'REG': {
            'lat': 17.5052679,
            'lon': 82.7880359
        },
        'YLM': {
            'lat': 17.5534876,
            'lon': 82.8428433
        },
        'NASP': {
            'lat': 17.6057255,
            'lon': 82.8899697
        },
        'BVM': {
            'lat': 17.6600783,
            'lon': 82.9259044
        },
        'KSK': {
            'lat': 17.6732113,
            'lon': 82.9564764
        },
        'AKP': {
            'lat': 17.6934772,
            'lon': 83.0049398
        },
        'THY': {
            'lat': 17.6865433,
            'lon': 83.0665228
        },
        'DVD': {
            'lat': 17.7030476,
            'lon': 83.1485371
        },
        'NS': {
            'lat': 16.7713563,
            'lon': 78.7213753
        },
        'MTM': {
            'lat': 16.5642053,
            'lon': 80.4050177
        },
        'RMV': {
            'lat': 16.5262612,
            'lon': 80.6781754
        },
        'GDV': {
            'lat': 16.4343363,
            'lon': 80.9708003
        },
        'PAVP': {
            'lat': 16.5627033,
            'lon': 80.8368158
        },
        'GWM': {
            'lat': 16.5563023,
            'lon': 80.7933824
        },
        'GALA': {
            'lat': 16.5381503,
            'lon': 80.6707216
        },
        'MBD': {
            'lat': 16.5504386,
            'lon': 80.7132015
        }
    }


@st.cache_data(ttl=300)
def extract_station_codes(selected_stations, station_column=None):
    """Extract station codes from selected DataFrame using optimized approach"""
    selected_station_codes = []

    if selected_stations.empty:
        return selected_station_codes

    # Look for station code in 'CRD' or 'Station' column
    potential_station_columns = [
        'CRD', 'Station', 'Station Code', 'station', 'STATION'
    ]

    # Try each potential column
    for col_name in potential_station_columns:
        if col_name in selected_stations.columns:
            for _, row in selected_stations.iterrows():
                if pd.notna(row[col_name]):
                    # Extract station code from text (may contain additional details)
                    text_value = str(row[col_name]).strip()

                    # Handle 'CRD' column which might have format "NZD ..."
                    if col_name == 'CRD':
                        # Extract first word which is likely the station code
                        parts = text_value.split()
                        if parts:
                            code = parts[0].strip()
                            if code and code not in selected_station_codes:
                                selected_station_codes.append(code)
                    else:
                        # For other columns, use the full value
                        if text_value and text_value not in selected_station_codes:
                            selected_station_codes.append(text_value)

    # If still no codes found, try a more generic approach with any column
    if not selected_station_codes:
        for col in selected_stations.columns:
            if any(keyword in col for keyword in
                   ['station', 'Station', 'STATION', 'Running', 'CRD']):
                for _, row in selected_stations.iterrows():
                    if pd.notna(row[col]):
                        text = str(row[col])
                        # Try to extract a station code (usually 2-5 uppercase letters)
                        words = text.split()
                        for word in words:
                            word = word.strip()
                            if 2 <= len(word) <= 5 and word.isupper():
                                if word not in selected_station_codes:
                                    selected_station_codes.append(word)

    return selected_station_codes


# Initialize sessionstate
initialize_session_state()

# Main page title
st.title("TRAIN TRACKING")

# Add a refresh button atthe top with just an icon
col1, col2 = st.columns((10, 2))
with col2:
    if st.button("🔄", type="primary"):
        st.rerun()
try:
    data_handler = st.session_state['icms_data_handler']

    # Load data with feedback
    with st.spinner("Loading data..."):
        success, message = data_handler.load_data_from_drive()

    if success:
        ## Show last update time
        if data_handler.last_update:
            # Convert last update to IST (UTC+5:30)
            last_update_ist = data_handler.last_update + timedelta(hours=5,
                                                                   minutes=30)
            st.info(
                f"Last updated: {last_update_ist.strftime('%Y-%m-%d %H:%M:%S')} IST"
            )

        # Get cached data
        cached_data = data_handler.get_cached_data()

        if cached_data:
            # Convert to DataFrame
            df = pd.DataFrame(cached_data)

            if not df.empty:
                # Skip first two rows (0 and 1) and reset index
                df = df.iloc[2:].reset_index(drop=True)

                # Safe conversion of NaN values to None
                def safe_convert(value):
                    if pd.isna(value) or pd.isnull(value):
                        return None
                    return str(value) if value is not None else None

                # Apply safe conversion to all elements
                for column in df.columns:
                    df[column] = df[column].map(safe_convert)

                # Get and print all column names for debugging
                logger.debug(f"Available columns: {df.columns.tolist()}")

                # Extract stations for map
                stations = extract_stations_from_data(df)

                # Drop unwanted columns - use exact column names with proper spacing
                columns_to_drop = [
                    'Sr.',
                    'Exit Time for NLT Status',
                    'Start date',
                    'Event',
                    'Train Class ',
                    # Try different column name variations
                    'Scheduled [ Entry - Exit ]',
                    'Scheduled [Entry - Exit]',
                    'Scheduled[ Entry - Exit ]',
                    'Scheduled[Entry - Exit]',
                    'Scheduled [ Entry-Exit ]',
                    'Scheduled [Entry-Exit]',
                    'scheduled[Entry-Exit]',
                    'DivisionalActual[ Entry - Exit ]',
                    'Divisional Actual [Entry- Exit]',
                    'Divisional Actual[ Entry-Exit ]',
                    'Divisional Actual[ Entry - Exit ]',
                    'DivisionalActual[ Entry-Exit ]',
                    'Divisional Actual [Entry-Exit]'
                ]

                # Drop each column individually if it exists
                for col in columns_to_drop:
                    if col in df.columns:
                        df = df.drop(columns=[col])
                        logger.debug(f"Dropped column: {col}")

                # Define styling function with specific colors for train types
                def highlight_delay(data):
                    styles = pd.DataFrame('',
                                          index=data.index,
                                          columns=data.columns)

                    # Apply red color only to the 'Delay' column if it exists
                    if 'Delay' in df.columns:
                        styles['Delay'] = df['Delay'].apply(
                            lambda x: 'color: red; font-weight: bold'
                            if x and is_positive_or_plus(x) else '')

                    # Style train number column based on the first digit of train number
                    train_number_cols = ['Train No.', 'Train Name']
                    for train_col in train_number_cols:
                        if train_col in df.columns:
                            # Set base styling for all train numbers
                            styles[
                                train_col] = 'background-color: #e9f7fe; font-weight: bold; border-left: 3px solid #0066cc'

                            # Apply specific color based on first digit of train number
                            for idx, train_no in df[train_col].items():
                                if pd.notna(train_no):
                                    train_no_str = str(train_no).strip()
                                    if train_no_str and len(train_no_str) > 0:
                                        first_digit = train_no_str[0]

                                        # Apply colors based on first digit
                                        if first_digit == '1':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #d63384; font-weight: bold; border-left: 3px solid #d63384'
                                        elif first_digit == '2':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #6f42c1; font-weight: bold; border-left: 3px solid #6f42c1'
                                        elif first_digit == '3':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #0d6efd; font-weight: bold; border-left: 3px solid #0d6efd'
                                        elif first_digit == '4':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #20c997; font-weight: bold; border-left: 3px solid #20c997'
                                        elif first_digit == '5':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #198754; font-weight: bold; border-left: 3px solid #198754'
                                        elif first_digit == '6':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #0dcaf0; font-weight: bold; border-left: 3px solid #0dcaf0'
                                        elif first_digit == '7':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #fd7e14; font-weight: bold; border-left: 3px solid #fd7e14'
                                        elif first_digit == '8':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #dc3545; font-weight: bold; border-left: 3px solid #dc3545'
                                        elif first_digit == '9':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #6610f2; font-weight: bold; border-left: 3px solid #6610f2'
                                        else:
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #333333; font-weight: bold; border-left: 3px solid #333333'

                    # Hidden column name
                    from_to_col = 'FROM-TO'

                    # Check if the hidden column exists in the DataFrame
                    if from_to_col in df.columns:
                        for idx, value in df[from_to_col].items():
                            if pd.notna(value):
                                logger.info(
                                    f"Processing row {idx} with value: {value}"
                                )

                                extracted_value = str(value).split(
                                    ' ')[0].upper()
                                logger.debug(
                                    f"FROM-TO value: {value}, extracted value: {extracted_value}"
                                )

                                font_styles = {
                                    'DMU': 'color: blue; font-weight: bold; ',
                                    'MEM': 'color: blue; font-weight: bold; ',
                                    'SUF':
                                    'color: #e83e8c; font-weight: bold; ',
                                    'MEX':
                                    'color: #e83e8c; font-weight: bold; ',
                                    'VND':
                                    'color: #e83e8c; font-weight: bold; ',
                                    'RJ':
                                    'color: #e83e8c; font-weight: bold; ',
                                    'PEX':
                                    'color: #e83e8c; font-weight: bold; ',
                                    'TOD':
                                    'color: #fd7e14; font-weight: bold; '
                                }

                                # Apply train type styling
                                for col in styles.columns:
                                    style_to_apply = font_styles.get(
                                        extracted_value, '')
                                    if style_to_apply:
                                        styles.loc[idx, col] += style_to_apply

                    # Train number styling is now handled in the earlier section

                    return styles

                # Add a "Select" column at the beginning of the DataFrame for checkboxes
                if 'Select' not in df.columns:
                    df.insert(0, 'Select', False)

                # Get station column name
                station_column = next(
                    (col for col in df.columns
                     if col in ['Station', 'station', 'STATION']), None)

                # Refresh animation placeholder
                refresh_table_placeholder = st.empty()
                create_pulsing_refresh_animation(refresh_table_placeholder,
                                                 "Refreshing data...")

                # Apply styling to the dataframe
                styled_df = df.style.apply(highlight_delay, axis=None)

                # Replacing just the filter implementation to look for "(+X)" pattern:

                # Filter rows containing plus sign in brackets like "(+5)"
                def contains_plus_in_brackets(row):
                    # Use regex to find values with plus sign inside brackets like "(+5)"
                    row_as_str = row.astype(str).str.contains('\(\+\d+\)',
                                                              regex=True)
                    return row_as_str.any()

                # Apply filter to dataframe
                filtered_df = df[df.apply(contains_plus_in_brackets, axis=1)]

                # If filtered dataframe is empty, show a message and use original dataframe
                if filtered_df.empty:
                    st.warning(
                        "No rows found containing values with plus sign in brackets. Showing all data."
                    )
                    display_df = df
                else:
                    st.success(f"Showing {len(filtered_df)} rows'")
                    display_df = filtered_df

                # Process the FROM-TO column to extract only the first part (MEX, SUF, etc.)
                if 'FROM-TO' in display_df.columns:
                    # Extract only the first part of the FROM-TO column (e.g., "MEX", "SUF", "TOD")
                    logger.info(f"Found column: FROM-TO")
                    for idx, value in enumerate(display_df['FROM-TO']):
                        if pd.notna(value) and isinstance(value, str):
                            # Get the first part before any brackets or spaces
                            first_part = value.split('[')[0].split(' ')[0].strip()
                            # Log for debugging
                            logger.info(f"Train {idx} - FROM-TO: '{value}', First three chars: '{first_part}'")
                            # Replace the value with just the first part
                            display_df.at[idx, 'FROM-TO'] = first_part

                # Reset index and add a sequential serial number column
                display_df = display_df.reset_index(drop=True)

                # Add a sequential S.No. column at the beginning (before Select)
                display_df.insert(0, '#', range(1, len(display_df) + 1))

                # Create style info for train numbers
                if 'Train No.' in display_df.columns:
                    # Add a column with train number class for styling
                    def get_train_class(train_no):
                        if train_no is None or str(train_no).strip() == '':
                            return ''
                        train_no_str = str(train_no).strip()
                        if not train_no_str or len(train_no_str) == 0:
                            return ''
                        try:
                            first_digit = train_no_str[0]
                            return f'train-{first_digit}'
                        except:
                            return ''

                    # Set the train class attribute that will be used for styling
                    # This column will be used temporarily and removed before displaying the table
                    display_df['Train Class'] = display_df['Train No.'].apply(
                        get_train_class)

                    # Custom styler to add data attributes to cells
                    def apply_train_class_styler(df):
                        # Style the Train No column based on first digit
                        styles = []
                        for i, row in df.iterrows():
                            train_class = row.get('Train Class', '')
                            if train_class:
                                styles.append({
                                    'selector':
                                    f'td:nth-child(3)',
                                    'props':
                                    [('data-train-class', train_class)]
                                })
                        return styles

                    # Apply the styler function to add data attributes
                    # (Note: This may not be supported in all Streamlit versions)

                # Log FROM-TO values for debugging
                def log_from_to_values(df):
                    """Print FROM-TO values for each train to help with debugging"""

                    from_to_columns = ['FROM-TO', 'FROM_TO']
                    for col_name in from_to_columns:
                        if col_name in df.columns:
                            logger.info(f"Found column: {col_name}")
                            for idx, value in df[col_name].items():
                                if pd.notna(value):
                                    first_three = str(value).upper()[:3]
                                    logger.info(
                                        f"Train {idx} - {col_name}: '{value}', First three chars: '{first_three}'"
                                    )

                # Call the logging function
                log_from_to_values(display_df)

                # Create a layout for train data and map side by side
                train_data_col, map_col = st.columns((2.4, 2.6))

                # Train data section
                with train_data_col:
                    # Add a card for the table content
                    st.markdown(
                        '<div class="card shadow-sm mb-3"><div class="card-header bg-primary text-white d-flex justify-content-between align-items-center"><span>Train Data</span><span class="badge bg-light text-dark rounded-pill">Select stations to display on map</span></div><div class="card-body p-0">',
                        unsafe_allow_html=True)

                    # Use combination approach: Standard data_editor for selection + styled display

                    # Check if Select column already exists
                    if 'Select' not in display_df.columns:
                        display_df.insert(0, 'Select',
                                          False)  # Add selection column
                    
                    # Fill any NaN values in the Select column with False to prevent filtering errors
                    display_df['Select'] = display_df['Select'].fillna(False)

                    # Display the main data table with integrated selection checkboxes
                    st.subheader("Train Status Data")

                    # Apply cell styling function to color the train numbers
                    styled_df = display_df.copy()

                    # Remove the "Train Class" column if it exists before displaying
                    if 'Train Class' in styled_df.columns:
                        styled_df = styled_df.drop(columns=['Train Class'])

                    # Import the styling function from color_train_formatter
                    from color_train_formatter import style_train_dataframe

                    # Use Streamlit's built-in dataframe with styling from our formatter
                    edited_df = st.data_editor(
                        style_train_dataframe(styled_df,
                                              train_column='Train No.'),
                        hide_index=True,
                        column_config={
                            "#":
                            st.column_config.NumberColumn("#",
                                                          help="Serial Number",
                                                          format="%d"),
                            "Select":
                            st.column_config.CheckboxColumn(
                                "Select",
                                help="Select to show on map",
                                default=False),
                            "Train No.":
                            st.column_config.TextColumn("Train No.",
                                                        help="Train Number"),
                            "FROM-TO":
                            st.column_config.TextColumn(
                                "FROM-TO", help="Source to Destination"),
                            "IC Entry Delay":
                            st.column_config.TextColumn("IC Entry Delay",
                                                        help="Entry Delay"),
                            "Delay":
                            st.column_config.TextColumn(
                                "Delay", help="Delay in Minutes")
                        },
                        disabled=[
                            col for col in display_df.columns
                            if col != 'Select'
                        ],
                        use_container_width=True,
                        height=600,
                        num_rows="dynamic")

                    # Add a footer to the card with information about the data
                    # Fill NaN values in the Select column to prevent filtering errors
                    edited_df['Select'] = edited_df['Select'].fillna(False)
                    selected_count = len(edited_df[edited_df['Select'] == True])
                    st.markdown(
                        f'<div class="card-footer bg-light d-flex justify-content-between align-items-center"><span>Total Rows: {len(display_df)}</span><span>Selected: {selected_count}</span></div>',
                        unsafe_allow_html=True)
                    st.markdown('</div></div>', unsafe_allow_html=True)

                # Map section
                with map_col:
                    # Add a card for the map content
                    st.markdown(
                        '<div class="card mb-3"><div class="card-header bg-secondary text-white d-flex justify-content-between align-items-center"><span>Interactive GPS Map</span><span class="badge bg-light text-dark rounded-pill">Showing selected stations</span></div><div class="card-body p-0">',
                        unsafe_allow_html=True)

                    # Create the interactive map
                    # Check if we need to rebuild the map from scratch or can use session state

                    # Extract station codes from selected rows
                    # Ensure we're using boolean indexing with no NaN values
                    selected_rows = edited_df[edited_df['Select'] == True]
                    # Determine which column contains station codes
                    station_column = 'Station' if 'Station' in edited_df.columns else 'CRD'
                    selected_station_codes = extract_station_codes(
                        selected_rows, station_column)

                    # Store the selected codes for comparison
                    if 'last_selected_codes' not in st.session_state:
                        st.session_state['last_selected_codes'] = []

                    # Convert to frozenset for comparison (order doesn't matter)
                    current_selected = frozenset(selected_station_codes)
                    last_selected = frozenset(
                        st.session_state['last_selected_codes'])

                    # Update the stored codes
                    st.session_state[
                        'last_selected_codes'] = selected_station_codes

                    # Create a folium map with fewer features for better performance
                    m = folium.Map(
                        location=[16.5167,
                                  80.6167],  # Centered around Vijayawada
                        zoom_start=7,
                        control_scale=True,
                        prefer_canvas=True
                    )  # Use canvas renderer for better performance

                    # Use a lightweight tile layer
                    folium.TileLayer(
                        tiles='CartoDB positron',  # Lighter map style
                        attr='&copy; OpenStreetMap contributors',
                        opacity=0.7).add_to(m)

                    # Get cached station coordinates
                    station_coords = get_station_coordinates()

                    # Add markers efficiently
                    displayed_stations = []
                    valid_points = []

                    # Add ALL stations with clear labels
                    for code, coords in station_coords.items():
                        # Skip selected stations - they'll get bigger markers later
                        if code in selected_station_codes:
                            continue

                        # Add small circle markers for all stations
                        folium.CircleMarker([coords['lat'], coords['lon']],
                                            radius=3,
                                            color='#800000',
                                            fill=True,
                                            fill_color='gray',
                                            fill_opacity=0.6,
                                            tooltip=f"{code}").add_to(m)

                        # Add permanent text label for station with dynamic width
                        label_width = max(
                            len(code) * 7,
                            20)  # Adjust width based on station code length
                        folium.Marker(
                            [coords['lat'], coords['lon'] + 0.005],
                            icon=folium.DivIcon(
                                icon_size=(0, 0),
                                icon_anchor=(0, 0),
                                html=
                                f'<div style="display:inline-block; min-width:{label_width}px; font-size:10px; background-color:rgba(255,255,255,0.7); padding:1px 3px; border-radius:2px; border:1px solid #800000; text-align:center;">{code}</div>'
                            )).add_to(m)

                    # Add the selected stations with train icons and prominent labels
                    for code in selected_station_codes:
                        normalized_code = code.strip().upper()

                        if normalized_code in station_coords:
                            lat = station_coords[normalized_code]['lat']
                            lon = station_coords[normalized_code]['lon']

                            # Add a large train icon marker for selected stations
                            folium.Marker(
                                [lat, lon],
                                popup=f"<b>{normalized_code}</b>",
                                tooltip=normalized_code,
                                icon=folium.Icon(color='red',
                                                 icon='train',
                                                 prefix='fa'),
                            ).add_to(m)

                            # Add a prominent label with bolder styling and dynamic width
                            label_width = max(
                                len(normalized_code) * 10,
                                30)  # Larger width for selected stations
                            folium.Marker(
                                [lat, lon + 0.01],
                                icon=folium.DivIcon(
                                    icon_size=(0, 0),
                                    icon_anchor=(0, 0),
                                    html=
                                    f'<div style="display:inline-block; min-width:{label_width}px; font-size:14px; font-weight:bold; background-color:rgba(255,255,255,0.9); padding:3px 5px; border-radius:3px; border:2px solid red; text-align:center;">{normalized_code}</div>'
                                )).add_to(m)

                            displayed_stations.append(normalized_code)
                            valid_points.append([lat, lon])

                    # Add railway lines between selected stations if more than one
                    if len(valid_points) > 1:
                        folium.PolyLine(valid_points,
                                        weight=2,
                                        color='gray',
                                        opacity=0.8,
                                        dash_array='5, 10').add_to(m)

                    # Use a feature that allows map to remember its state (zoom, pan position)
                    st_folium(m, width=None, height=600, key="persistent_map")

                    st.markdown('</div></div>', unsafe_allow_html=True)

                    # Show success message if stations are selected
                    if displayed_stations:
                        st.success(
                            f"Showing {len(displayed_stations)} selected stations on the map"
                        )
                    else:
                        st.info(
                            "Select stations in the table to display them on the map"
                        )

                # Add instructions in collapsible section
                with st.expander("Map Instructions"):
                    st.markdown("""
                    <div class="card">
                        <div class="card-header bg-light">
                            Using the Interactive Map
                        </div>
                        <div class="card-body">
                            <ul class="list-group list-group-flush">
                                <li class="list-group-item">Select stations using the checkboxes in the table</li>
                                <li class="list-group-item">Selected stations will appear with red train markers on the map</li>
                                <li class="list-group-item">All other stations are shown as small gray dots</li>
                                <li class="list-group-item">Railway lines automatically connect selected stations in sequence</li>
                                <li class="list-group-item">Zoom and pan the map to explore different areas</li>
                            </ul>
                        </div>
                    </div>
                    """,
                                unsafe_allow_html=True)

                refresh_table_placeholder.empty(
                )  # Clear the placeholder after table display

            else:
                st.error("No data available in the cached data frame")
        else:
            st.error(f"Error: No cached data available. {message}")
    else:
        st.error(f"Error loading data: {message}")
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    logger.exception("Exception in main app")


# Function to check if a value is positive or contains (+)
def is_positive_or_plus(value):
    try:
        if value is None:
            return False

        if isinstance(value, str):
            # Check if the string contains a plus sign
            if '+' in value:
                return True

            # Clean the string of any non-numeric characters except minus sign and decimal point
            # First handle the case with multiple values (like "-7 \xa0-36")
            if '\xa0' in value or '  ' in value:
                # Take just the first part if there are multiple numbers
                value = value.split('\xa0')[0].split('  ')[0].strip()

            # Remove parentheses and other characters
            clean_value = value.replace('(', '').replace(')', '').strip()

            # Try to convert to float
            if clean_value:
                try:
                    return float(clean_value) > 0
                except ValueError:
                    # If conversion fails, check if it starts with a minus sign
                    return not clean_value.startswith('-')
        elif isinstance(value, (int, float)):
            return value > 0
    except Exception as e:
        logger.error(f"Error in is_positive_or_plus: {str(e)}")
        return False
    return False


# Note: Custom formatter is already imported at the top of the file

# Footer
st.markdown("---")
st.markdown(
    '<div class="card"><div class="card-body text-center text-muted">© 2023 South Central Railway - Vijayawada Division</div></div>',
    unsafe_allow_html=True)
