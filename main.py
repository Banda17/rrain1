import streamlit as st
import pandas as pd
from data_handler import DataHandler
from ai_analyzer import AIAnalyzer
from visualizer import Visualizer
from utils import format_time_difference, create_status_badge, show_ai_insights
from database import init_db

# Initialize database
init_db()

# Page configuration
st.set_page_config(
    page_title="Train Tracking System",
    page_icon="🚂",
    layout="wide"
)

# Theme toggle in sidebar
st.sidebar.title("Settings")
if 'theme' not in st.session_state:
    st.session_state.theme = "light"

theme = st.sidebar.radio(
    "Choose Theme",
    ("Light", "Dark"),
    index=0 if st.session_state.theme == "light" else 1
)

# Apply theme
if theme == "Dark":
    st.session_state.theme = "dark"
    st.markdown("""
        <style>
        .stApp {
            background-color: #1E1E1E;
            color: #FFFFFF;
        }
        .stMarkdown {
            color: #FFFFFF;
        }
        .stDataFrame {
            background-color: #2D2D2D;
            color: #FFFFFF;
        }
        </style>
    """, unsafe_allow_html=True)
else:
    st.session_state.theme = "light"
    st.markdown("""
        <style>
        .stApp {
            background-color: #FFFFFF;
            color: #000000;
        }
        </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'data_handler' not in st.session_state:
    st.session_state.data_handler = DataHandler()
if 'ai_analyzer' not in st.session_state:
    st.session_state.ai_analyzer = AIAnalyzer()
if 'visualizer' not in st.session_state:
    st.session_state.visualizer = Visualizer()

# Main title
st.title("🚂 Train Tracking and Analysis System")

# File upload section
st.sidebar.header("Data Input")
train_details_file = st.sidebar.file_uploader("Upload Train Details JSON", type=['json'])
wtt_timings_file = st.sidebar.file_uploader("Upload WTT Timings JSON", type=['json'])

if train_details_file and wtt_timings_file:
    # Load data
    success, message = st.session_state.data_handler.load_json_data(
        train_details_file,
        wtt_timings_file
    )

    if success:
        # Get analyzed data
        status_table = st.session_state.data_handler.get_train_status_table()

        # Display current status
        st.header("Current Train Status")
        col1, col2 = st.columns([2, 1])

        with col1:
            # Display train position visualization
            fig = st.session_state.visualizer.create_train_position_map(status_table)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Display latest status
            latest_status = status_table.iloc[-1]
            st.markdown(f"**Current Station:** {latest_status['station']}")
            st.markdown(f"**Status:** {create_status_badge(latest_status['status'])}", unsafe_allow_html=True)
            st.markdown(f"**Time Difference:** {format_time_difference(latest_status['delay'])}")

        # Display detailed table
        st.header("Detailed Timing Analysis")
        st.dataframe(
            status_table[['station', 'time_actual', 'time_scheduled', 'status', 'delay']],
            use_container_width=True
        )

        # AI Analysis
        st.header("AI Analysis")
        col1, col2 = st.columns([1, 1])

        with col1:
            # Display delay distribution
            fig = st.session_state.visualizer.create_delay_histogram(status_table)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Display AI insights
            insights = st.session_state.ai_analyzer.analyze_historical_delays(status_table)
            show_ai_insights(insights)

            # Display prediction for selected station
            selected_station = st.selectbox("Select station for delay prediction", status_table['station'].unique())
            prediction = st.session_state.ai_analyzer.get_delay_prediction(status_table, selected_station)

            st.info(f"Predicted delay at {prediction['station']}: "
                   f"{prediction['predicted_delay']} minutes "
                   f"(Confidence: {prediction['confidence']}%)")
    else:
        st.error(message)
else:
    st.info("Please upload both JSON files to begin analysis")

# Footer
st.markdown("---")
st.markdown("Train Tracking System - AI-Powered Analysis")