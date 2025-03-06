import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add Bootstrap CSS and custom grid layout CSS
st.markdown("""
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <style>
        /* Custom styles to enhance Bootstrap */
        .stApp {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
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
""", unsafe_allow_html=True)

# Function to get station coordinates
def get_station_coordinates():
    """Cache station coordinates for faster access"""
    return {
        'BZA': {'name': 'Vijayawada', 'lat': 16.5167, 'lon': 80.6167},
        'GNT': {'name': 'Guntur', 'lat': 16.3067, 'lon': 80.4365},
        'VSKP': {'name': 'Visakhapatnam', 'lat': 17.6868, 'lon': 83.2185},
        # Add more stations as needed
    }

# Sample data
data = {
    'Train No.': ['12727', '12728', '17239', '17240'],
    'Train Name': ['Godavari Express', 'Godavari Express', 'Simhadri Express', 'Simhadri Express'],
    'Station': ['BZA', 'VSKP', 'VSKP', 'BZA'],
    'FROM-TO': ['BZA-VSKP', 'VSKP-BZA', 'VSKP-BZA', 'BZA-VSKP'],
    'Sch_Time': ['10:30', '18:45', '06:15', '22:30'],
    'Current Time': ['10:45', '19:10', '06:20', '22:45'],
    'Status': ['Running Late', 'Running Late', 'On Time', 'Running Late'],
    'Delay': ['+15', '+25', '+5', '+15'],
    'IC Entry Delay': ['10', '20', '5', '10']
}

df = pd.DataFrame(data)

# Add Select column for checkboxes if not present
if 'Select' not in df.columns:
    df.insert(0, 'Select', False)

# Page title
st.title("Train Tracking System - Vijayawada Division")

# Start the Bootstrap grid layout for side-by-side display
st.markdown('<div class="bs-grid-container">', unsafe_allow_html=True)

# Left section for the table
st.markdown('<div class="bs-grid-left">', unsafe_allow_html=True)

# Add a card for the table with Bootstrap styling
st.markdown('<div class="card shadow-sm mb-3"><div class="card-header bg-primary text-white d-flex justify-content-between align-items-center"><span>Train Data</span><span class="badge bg-light text-dark rounded-pill">Select stations to display on map</span></div><div class="card-body p-0">', unsafe_allow_html=True)

# Interactive data table with checkboxes for selection
edited_df = st.data_editor(
    df,
    hide_index=True,
    column_config={
        "Select": st.column_config.CheckboxColumn("Select", help="Select to show on map", default=False),
        "Train No.": st.column_config.TextColumn("Train No.", help="Train Number"),
        "Train Name": st.column_config.TextColumn("Train Name", help="Name of the train"),
        "Station": st.column_config.TextColumn("Station", help="Station Code"),
        "FROM-TO": st.column_config.TextColumn("FROM-TO", help="Source to Destination"),
        "Sch_Time": st.column_config.TextColumn("Scheduled Time", help="Scheduled Time"),
        "Current Time": st.column_config.TextColumn("Current Time", help="Current Time"),
        "Status": st.column_config.TextColumn("Status", help="Train Status"),
        "Delay": st.column_config.TextColumn("Delay", help="Delay in Minutes"),
        "IC Entry Delay": st.column_config.TextColumn("IC Entry Delay", help="Entry Delay")
    },
    disabled=[col for col in df.columns if col != 'Select'],
    use_container_width=True,
    height=600,
    num_rows="dynamic"
)

# Add a footer to the card with information about the data
selected_count = len(edited_df[edited_df['Select']])
st.markdown(f'<div class="card-footer bg-light d-flex justify-content-between align-items-center"><span>Total Rows: {len(df)}</span><span>Selected: {selected_count}</span></div>', unsafe_allow_html=True)
st.markdown('</div></div>', unsafe_allow_html=True)

# Close the left section
st.markdown('</div>', unsafe_allow_html=True)

# Right section for the map
st.markdown('<div class="bs-grid-right">', unsafe_allow_html=True)

# Add a card for the map
st.markdown('<div class="card mb-3"><div class="card-header bg-secondary text-white d-flex justify-content-between align-items-center"><span>Interactive GPS Map</span><span class="badge bg-light text-dark rounded-pill">Showing selected stations</span></div><div class="card-body p-0">', unsafe_allow_html=True)

# Get selected stations
selected_rows = edited_df[edited_df['Select']]
selected_station_codes = []
if 'Station' in selected_rows.columns:
    selected_station_codes = selected_rows['Station'].tolist()

# Create the interactive map
m = folium.Map(
    location=[16.5167, 80.6167],  # Centered around Vijayawada
    zoom_start=7,
    control_scale=True
)

# Add a basemap
folium.TileLayer(
    tiles='OpenStreetMap',
    attr='&copy; OpenStreetMap contributors',
    opacity=0.8
).add_to(m)

# Get station coordinates
station_coords = get_station_coordinates()

# Add markers for all stations
displayed_stations = []
valid_points = []

# First add all non-selected stations as dots
for code, info in station_coords.items():
    # Skip selected stations - they'll get bigger markers later
    if code in selected_station_codes:
        continue
        
    # Add small circle for the station
    folium.CircleMarker(
        [info['lat'], info['lon']],
        radius=3,
        color='#800000',  # Maroon red border
        fill=True,
        fill_color='gray',
        fill_opacity=0.6,
        opacity=0.8,
        tooltip=f"{code} - {info['name']}"
    ).add_to(m)

# Then add larger markers for selected stations
for code in selected_station_codes:
    if code in station_coords:
        info = station_coords[code]
        
        # Add train icon marker for selected stations
        folium.Marker(
            [info['lat'], info['lon']],
            popup=f"<b>{code}</b><br>{info['name']}<br>({info['lat']:.4f}, {info['lon']:.4f})",
            tooltip=code,
            icon=folium.Icon(color='red', icon='train', prefix='fa'),
            opacity=0.8
        ).add_to(m)
        
        displayed_stations.append(code)
        valid_points.append([info['lat'], info['lon']])

# Add railway lines between selected stations
if len(valid_points) > 1:
    folium.PolyLine(
        valid_points,
        weight=2,
        color='gray',
        opacity=0.8,
        dash_array='5, 10'
    ).add_to(m)

# Display the map
folium_static(m, width=650, height=600)

# Add a success message if stations are selected
if displayed_stations:
    st.success(f"Showing {len(displayed_stations)} selected stations on the map")
else:
    st.info("Select stations in the table to display them on the map")

st.markdown('</div></div>', unsafe_allow_html=True)

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
    """, unsafe_allow_html=True)

# Close the right section
st.markdown('</div>', unsafe_allow_html=True)

# Close the grid container
st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    '<div class="card"><div class="card-body text-center text-muted">© 2023 South Central Railway - Vijayawada Division</div></div>',
    unsafe_allow_html=True)
