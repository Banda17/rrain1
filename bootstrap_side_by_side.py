import streamlit as st

# Add Bootstrap CSS for the grid layout
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

# Create sample data (replace with your actual data)
import pandas as pd
data = {
    'Train No.': ['12727', '12728', '17239'],
    'Station': ['BZA', 'VSKP', 'GNT'],
    'Delay': ['+15', '0', '+20']
}
df = pd.DataFrame(data)
df.insert(0, 'Select', False)  # Add select column

# Start the Bootstrap grid layout - THIS IS THE KEY PART
st.markdown('<div class="bs-grid-container">', unsafe_allow_html=True)

# Left container for the table
st.markdown('<div class="bs-grid-left">', unsafe_allow_html=True)

# Table with Bootstrap styling
st.write("### Train Data")
edited_df = st.data_editor(
    df,
    hide_index=True,
    column_config={
        "Select": st.column_config.CheckboxColumn("Select", default=False),
    },
    disabled=[col for col in df.columns if col != 'Select'],
    use_container_width=True,
    height=500
)
st.markdown('</div>', unsafe_allow_html=True)  # Close left container

# Right container for the map
st.markdown('<div class="bs-grid-right">', unsafe_allow_html=True)

# Map content
st.write("### Interactive Map")
# Replace this with your actual map code
import folium
from streamlit_folium import folium_static
m = folium.Map(location=[16.5167, 80.6167], zoom_start=7)
folium_static(m, width=650, height=500)

st.markdown('</div>', unsafe_allow_html=True)  # Close right container

st.markdown('</div>', unsafe_allow_html=True)  # Close grid container

# The critical parts for side-by-side layout are:
# 1. The flex container: <div class="bs-grid-container">
# 2. The left column: <div class="bs-grid-left">
# 3. The right column: <div class="bs-grid-right">
# 4. Properly closing each div tag in reverse order
