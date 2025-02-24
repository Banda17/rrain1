import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd

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

# Create the base map
m = folium.Map(
    location=AP_CENTER,
    zoom_start=8,
    tiles="cartodb positron"
)

# Sample station coordinates (Replace these with actual GPS coordinates)
stations = {
    'BZA': {'name': 'Vijayawada', 'lat': 16.5167, 'lon': 80.6167},
    'GNT': {'name': 'Guntur', 'lat': 16.3067, 'lon': 80.4365},
    'VSKP': {'name': 'Visakhapatnam', 'lat': 17.6868, 'lon': 83.2185},
    'TUNI': {'name': 'Tuni', 'lat': 17.3572, 'lon': 82.5483},
    'RJY': {'name': 'Rajahmundry', 'lat': 17.0005, 'lon': 81.7799},
    'NLDA': {'name': 'Nalgonda', 'lat': 17.0575, 'lon': 79.2690},
}

# Controls
col1, col2 = st.columns([1, 2])
with col1:
    show_coords = st.checkbox("Show GPS Coordinates", value=True)
    show_station_list = st.checkbox("Show Station List", value=True)

# Add markers for each station
for code, info in stations.items():
    folium.Marker(
        [info['lat'], info['lon']],
        popup=f"{code} - {info['name']}",
        tooltip=code,
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)

# Add railway lines connecting stations (simplified)
station_points = [[info['lat'], info['lon']] for info in stations.values()]
folium.PolyLine(
    station_points,
    weight=2,
    color='gray',
    opacity=0.8,
    dash_array='5, 10'
).add_to(m)

# Display the map
folium_static(m, width=1000, height=600)

# Show station list if enabled
if show_station_list:
    st.subheader("Station Coordinates")

    # Create DataFrame for display
    stations_df = pd.DataFrame([
        {
            'Station Code': code,
            'Name': info['name'],
            'Latitude': info['lat'],
            'Longitude': info['lon']
        }
        for code, info in stations.items()
    ])

    if show_coords:
        st.dataframe(
            stations_df,
            use_container_width=True,
            height=400
        )
    else:
        st.dataframe(
            stations_df[['Station Code', 'Name']],
            use_container_width=True,
            height=400
        )

    st.info(f"Showing {len(stations)} stations")

# Add instructions for coordinate updates
st.markdown("""
### About GPS Coordinates
- Latitude: North-South position (-90° to 90°)
- Longitude: East-West position (-180° to 180°)
- Coordinates shown are in decimal degrees
""")