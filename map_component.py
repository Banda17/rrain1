import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
from typing import Dict, List, Optional
from map_utils import OfflineMapHandler

def render_gps_map(
    selected_stations: Optional[List[str]] = None,
    center_coordinates: List[float] = [16.5167, 80.6167],  # Default center at Vijayawada
    map_title: str = "Division Map View",
    height: int = 400
) -> None:
    """
    Renders a GPS map with the selected stations marked.
    This is a reusable component that can be included in any Streamlit page.

    Args:
        selected_stations: List of station codes to highlight on the map
        center_coordinates: Center coordinates for the map [lat, lon]
        map_title: Title to display above the map
        height: Height of the map in pixels
    """
    # Define station coordinates with actual GPS locations
    stations = {
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
        'PLH': {'name': 'Palasa', 'lat': 18.7726, 'lon': 84.4162},
        'GDR': {'name': 'Gudur', 'lat': 14.1483, 'lon': 79.8538},
        'TADI': {'name': 'Thadi', 'lat': 16.7520, 'lon': 79.9841},
        # Add more station coordinates from bhanu.json as needed
        'VNEC': {'name': 'Venkachalam', 'lat': 16.4805, 'lon': 80.5487},
        'GALA': {'name': 'Galakollu', 'lat': 16.4355, 'lon': 80.5842},
        'MBD': {'name': 'Mustabad', 'lat': 16.3980, 'lon': 80.6120},
        'GWM': {'name': 'Gunadala West', 'lat': 16.5310, 'lon': 80.6050},
        'PAVP': {'name': 'Pavuluru', 'lat': 16.5532, 'lon': 80.5892},
    }

    # Create a container for the map
    st.subheader(map_title)

    # Initialize the map
    map_container = st.container()

    with map_container:
        # Check if any stations are selected
        if not selected_stations or len(selected_stations) == 0:
            # Show a message when no stations are selected
            st.info("Please select stations from the table to display them on the map")
            # Still create a basic map to show the division area
            try:
                # Create a custom map bounds tuple with user-specified values
                custom_bounds = (12.2, 18.7, 78.3, 84.3)  # Fixed bounds as requested by user

                # Try to use OfflineMapHandler if map file is available
                map_handler = OfflineMapHandler('Vijayawada_Division_System_map_page-0001 (2).png')
                # Convert list to tuple for center coordinates and pass custom bounds
                m = map_handler.create_offline_map(
                    center=(center_coordinates[0], center_coordinates[1]),
                    custom_bounds=custom_bounds
                )

                if not m:
                    # Fall back to online map if offline map fails
                    m = folium.Map(location=center_coordinates, zoom_start=8)
            except Exception as e:
                st.warning(f"Using online map: {str(e)}")
                # Create a basic folium map as fallback
                m = folium.Map(location=center_coordinates, zoom_start=8)

            # Display the empty map
            folium_static(m, width=None, height=height)
            return

        try:
            # Create a custom map bounds tuple with user-specified values
            custom_bounds = (12.2, 18.7, 78.3, 84.3)  # Fixed bounds as requested by user

            # Try to use OfflineMapHandler if map file is available
            map_handler = OfflineMapHandler('Vijayawada_Division_System_map_page-0001 (2).png')
            # Convert list to tuple for center coordinates and pass custom bounds
            m = map_handler.create_offline_map(
                center=(center_coordinates[0], center_coordinates[1]),
                custom_bounds=custom_bounds
            )

            if not m:
                # Fall back to online map if offline map fails
                m = folium.Map(location=center_coordinates, zoom_start=8)
        except Exception as e:
            st.warning(f"Using online map: {str(e)}")
            # Create a basic folium map as fallback
            m = folium.Map(location=center_coordinates, zoom_start=8)

        # Add markers for selected stations
        selected_station_points = []
        for code in selected_stations:
            if code in stations:
                station = stations[code]
                popup_content = f"""
                <div style='font-family: Arial; font-size: 12px;'>
                    <b>{code} - {station['name']}</b><br>
                    Lat: {station['lat']:.4f}<br>
                    Lon: {station['lon']:.4f}
                </div>
                """

                # Add marker
                folium.Marker(
                    [station['lat'], station['lon']],
                    popup=folium.Popup(popup_content, max_width=200),
                    tooltip=f"{code} - {station['name']}",
                    icon=folium.Icon(color='red', icon='train', prefix='fa')
                ).add_to(m)

                # Add to points for railway line
                selected_station_points.append([station['lat'], station['lon']])

        # Add railway lines between selected stations if multiple stations
        if len(selected_station_points) > 1:
            folium.PolyLine(
                selected_station_points,
                weight=2,
                color='gray',
                opacity=0.8,
                dash_array='5, 10'
            ).add_to(m)

        # Display the map
        folium_static(m, width=None, height=height)

        # Show station count
        if selected_stations:
            st.info(f"Showing {len(selected_stations)} stations on the map")