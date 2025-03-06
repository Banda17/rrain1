import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# Add Bootstrap CSS and grid layout CSS
st.markdown("""
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        /* Bootstrap grid container for side-by-side layout */
        .bs-grid-container {
            display: flex;
            width: 100%;
            margin: 0;
            padding: 0;
        }
        .bs-grid-left {
            flex: 6;
            padding-right: 10px;
            min-width: 600px;
        }
        .bs-grid-right {
            flex: 6;
            padding-left: 0;
            min-width: 600px;
        }
        @media (max-width: 1200px) {
            .bs-grid-container {
                flex-direction: column;
            }
            .bs-grid-left, .bs-grid-right {
                flex: 100%;
                padding: 0;
                width: 100%;
                min-width: 100%;
            }
        }
    </style>
""", unsafe_allow_html=True)

# Create sample data for demonstration
data = {
    'Train No.': ['12727', '12728', '17239', '17240'],
    'Station': ['BZA', 'VSKP', 'GNT', 'RJY'],
    'Status': ['Running Late', 'On Time', 'Running Late', 'On Time'],
    'Delay': ['+15', '0', '+20', '0']
}
df = pd.DataFrame(data)

# Add Select column for checkboxes
if 'Select' not in df.columns:
    df.insert(0, 'Select', False)

# Start the Bootstrap grid layout - THIS IS THE KEY PART FOR SIDE-BY-SIDE LAYOUT
st.markdown('<div class="bs-grid-container">', unsafe_allow_html=True)

# Left container for the table
st.markdown('<div class="bs-grid-left">', unsafe_allow_html=True)

# Table with Bootstrap styling
st.markdown('<div class="card shadow-sm mb-3"><div class="card-header bg-primary text-white">Train Data</div><div class="card-body p-0">', unsafe_allow_html=True)
edited_df = st.data_editor(
    df,
    hide_index=True,
    column_config={
        "Select": st.column_config.CheckboxColumn("Select", help="Select to show on map", default=False),
    },
    disabled=[col for col in df.columns if col != 'Select'],
    use_container_width=True,
    height=600,
    num_rows="dynamic"
)
st.markdown('</div></div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # Close left container

# Right container for the map
st.markdown('<div class="bs-grid-right">', unsafe_allow_html=True)

# Map with Bootstrap styling
st.markdown('<div class="card mb-3"><div class="card-header bg-secondary text-white">Interactive Map</div><div class="card-body p-0">', unsafe_allow_html=True)
m = folium.Map(location=[16.5167, 80.6167], zoom_start=7)
folium_static(m, width=650, height=600)
st.markdown('</div></div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # Close right container

st.markdown('</div>', unsafe_allow_html=True)  # Close grid container

# The critical parts for side-by-side layout are:
# 1. The flex container: <div class="bs-grid-container">
# 2. The left column: <div class="bs-grid-left">
# 3. The right column: <div class="bs-grid-right">
# 4. Properly closing each div tag in reverse order
