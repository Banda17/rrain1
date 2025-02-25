import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import os
from map_utils import OfflineMapHandler

# Page configuration
st.set_page_config(
    page_title="Map View - Train Tracking System",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Division Map View")
st.markdown("""
This interactive map shows the stations in Vijayawada Division with their GPS coordinates.
Use the controls below to customize the view.
""")

# Define Andhra Pradesh center coordinates
AP_CENTER = [16.5167, 80.6167]  # Centered around Vijayawada

# Initialize offline map handler
map_handler = OfflineMapHandler('Vijayawada_Division_System_map_page-0001 (2).png')

@st.cache_data(ttl=3600)  # Cache station data for 1 hour
def get_station_data():
    """Get cached station coordinate data"""
    return {
        'BZA': {'name': 'Vijayawada', 'lat': 16.5167, 'lon': 80.6167},
        'GNT': {'name': 'Guntur', 'lat': 16.3067, 'lon': 80.4365},
        'VSKP': {'name': 'Visakhapatnam', 'lat': 17.6868, 'lon': 83.2185},
        'TUNI': {'name': 'Tuni', 'lat': 17.3572, 'lon': 82.5483},
        'RJY': {'name': 'Rajahmundry', 'lat': 17.0005, 'lon': 81.7799},
        'NLDA': {'name': 'Nalgonda', 'lat': 17.0575, 'lon': 79.2690},
        'MTM': {'name': 'Mangalagiri', 'lat': 16.4307, 'lon': 80.5525},
        'NDL': {'name': 'Nidadavolu', 'lat': 16.9107, 'lon': 81.6717},
        'ANV': {'name': 'Anakapalle', 'lat': 17.6910, 'lon': 83.0037},
        'VZM': {'name': 'Vizianagaram', 'lat': 18.1066, 'lon': 83.4205},
        'SKM': {'name': 'Srikakulam', 'lat': 18.2949, 'lon': 83.8935},
        'PLH': {'name': 'Palasa', 'lat': 18.7726, 'lon': 84.4162}
    }

@st.cache_data(ttl=3600)  # Cache DataFrame creation
def create_station_dataframe(_stations):
    """Create cached DataFrame for station selection.
    Using underscore prefix for argument to prevent Streamlit from hashing it."""
    return pd.DataFrame([
        {
            'Select': False,
            'Station Code': code,
            'Name': info['name'],
            'Latitude': info['lat'],
            'Longitude': info['lon']
        }
        for code, info in _stations.items()
    ])

# Get cached station data
stations = get_station_data()
stations_df = create_station_dataframe(stations)

# Controls
st.subheader("Station Selection")
st.markdown("Select stations to display on the map:")

# Make the dataframe interactive with checkboxes
edited_df = st.data_editor(
    stations_df,
    hide_index=True,
    column_config={
        "Select": st.column_config.CheckboxColumn(
            "Select",
            help="Select to show on map",
            default=False
        )
    },
    disabled=["Station Code", "Name", "Latitude", "Longitude"]
)

# Get selected stations
selected_stations = edited_df[edited_df['Select']]

# Create the map with offline support
m = map_handler.create_offline_map(_center=tuple(AP_CENTER))

if not m:
    st.error("Failed to load offline map. Please check the map file.")
    st.stop()

# Add markers only for selected stations
if not selected_stations.empty:
    # Add markers for selected stations
    for _, station in selected_stations.iterrows():
        # Create custom popup content
        popup_content = f"""
        <div style='font-family: Arial; font-size: 12px;'>
            <b>{station['Station Code']} - {station['Name']}</b><br>
            Lat: {station['Latitude']:.4f}<br>
            Lon: {station['Longitude']:.4f}
        </div>
        """

        folium.Marker(
            [station['Latitude'], station['Longitude']],
            popup=folium.Popup(popup_content, max_width=200),
            tooltip=station['Station Code'],
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)

    # Add railway lines between selected stations
    if len(selected_stations) > 1:
        station_points = [[row['Latitude'], row['Longitude']] for _, row in selected_stations.iterrows()]
        folium.PolyLine(
            station_points,
            weight=2,
            color='gray',
            opacity=0.8,
            dash_array='5, 10'
        ).add_to(m)

# Display the map
st.subheader("Interactive Map")
folium_static(m, width=1000, height=600)

# Show selection summary
if not selected_stations.empty:
    st.success(f"Showing {len(selected_stations)} selected stations on the map")
else:
    st.info("Select stations from the table above to display them on the map")

# Add instructions
st.markdown("""
### About GPS Coordinates
- Latitude: North-South position (-90° to 90°)
- Longitude: East-West position (-180° to 180°)
- Coordinates shown are in decimal degrees
- Map is loaded from local storage for offline access
""")