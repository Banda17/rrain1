import streamlit as st
import folium
from folium import plugins
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Train Map View - Train Tracking System",
    page_icon="🗺️",
    layout="wide"
)

# Initialize session state for map data
if 'map_data' not in st.session_state:
    st.session_state['map_data'] = {
        'stations': {
            'VNEC': {'lat': 17.3974, 'lon': 78.5819},  # Secunderabad
            'GALA': {'lat': 17.4760, 'lon': 78.5538},  # Gala
            'MBD': {'lat': 17.4345, 'lon': 78.4877},   # Malakpet
            'GWM': {'lat': 17.3827, 'lon': 78.5489},   # Gandhigram
            'PAVP': {'lat': 17.3689, 'lon': 78.5578},  # Pavalavagu
            'BZA': {'lat': 16.5162, 'lon': 80.6742},   # Vijayawada
        }
    }

# Title and description
st.title("🗺️ Train Network Map")
st.markdown("Interactive visualization of train stations and routes")

def create_map():
    """Create the base map centered on the network"""
    # Calculate center point from all stations
    stations = st.session_state['map_data']['stations']
    center_lat = sum(s['lat'] for s in stations.values()) / len(stations)
    center_lon = sum(s['lon'] for s in stations.values()) / len(stations)
    
    # Create the map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles="cartodb positron"
    )
    
    # Add station markers
    for station_name, coords in stations.items():
        folium.Marker(
            [coords['lat'], coords['lon']],
            popup=station_name,
            icon=folium.Icon(color='red', icon='train', prefix='fa')
        ).add_to(m)
        
    # Add lines connecting stations in sequence
    station_list = list(stations.items())
    for i in range(len(station_list) - 1):
        station1 = station_list[i]
        station2 = station_list[i + 1]
        folium.PolyLine(
            locations=[
                [station1[1]['lat'], station1[1]['lon']],
                [station2[1]['lat'], station2[1]['lon']]
            ],
            weight=2,
            color='blue',
            opacity=0.8
        ).add_to(m)
    
    return m

# Create two columns for the layout
col1, col2 = st.columns([3, 1])

with col1:
    # Display the map
    st.subheader("Network Map")
    map_obj = create_map()
    folium_static(map_obj)

with col2:
    # Add controls and information
    st.subheader("Station Information")
    selected_station = st.selectbox(
        "Select a station",
        options=list(st.session_state['map_data']['stations'].keys())
    )
    
    if selected_station:
        st.info(f"Selected Station: {selected_station}")
        coords = st.session_state['map_data']['stations'][selected_station]
        st.write(f"Latitude: {coords['lat']}")
        st.write(f"Longitude: {coords['lon']}")
        
        # Add station-specific information here
        st.markdown("### Trains at this station")
        if 'data_handler' in st.session_state:
            station_data = st.session_state['data_handler'].get_station_data(selected_station)
            if station_data:
                st.dataframe(station_data)
            else:
                st.write("No trains currently at this station")
