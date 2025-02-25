import streamlit as st
from typing import Dict

def format_time_difference(minutes: int) -> str:
    """Format time difference in a readable format"""
    if minutes == 0:
        return "On time"
    elif minutes > 0:
        return f"{minutes} minutes late"
    else:
        return f"{abs(minutes)} minutes early"

def create_status_badge(status: str) -> str:
    """Create HTML-like badge for status"""
    color_map = {
        "EARLY": "blue",
        "LATE": "red",
        "ON TIME": "green",
        "UNKNOWN": "gray"
    }
    
    status_type = status.split()[0]
    color = color_map.get(status_type, "gray")
    
    return f"""
    <span style='
        background-color: {color};
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 0.5rem;
        font-size: 0.8rem;
    '>
        {status}
    </span>
    """

def show_ai_insights(insights: Dict):
    """Display AI insights in a formatted way"""
    st.subheader("AI Analysis Insights")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Average Delay",
            f"{insights['average_delay']} min",
            delta=None
        )
    
    with col2:
        st.metric(
            "Reliability Score",
            f"{insights['reliability_score']}%",
            delta=None
        )
    
    with col3:
        st.metric(
            "Anomalies Detected",
            insights['anomaly_count'],
            delta=None
        )
