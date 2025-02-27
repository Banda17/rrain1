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
    height: int = 400,
    selected_df: Optional[pd.DataFrame] = None  # New parameter to directly receive selected DataFrame
) -> None:
    """
    Renders a GPS map with the selected stations marked.
    This is a reusable component that can be included in any Streamlit page.

    Args:
        selected_stations: List of station codes to highlight on the map
        center_coordinates: Center coordinates for the map [lat, lon]
        map_title: Title to display above the map
        height: Height of the map in pixels
        selected_df: DataFrame containing the selected stations with their coordinates
    """
    # Load station coordinates from CSV file
    try:
        station_df = pd.read_csv('attached_assets/station_coordinates (1).csv')
        # Create dictionary of station coordinates from the DataFrame
        stations = {}
        for _, row in station_df.iterrows():
            if not pd.isna(row['Station']) and not pd.isna(row['Latitude']) and not pd.isna(row['Longitude']):
                stations[row['Station']] = {
                    'name': row['Station'],  # Using station code as name if no name column
                    'lat': float(row['Latitude']),
                    'lon': float(row['Longitude'])
                }
    except Exception as e:
        st.warning(f"Error loading station coordinates from CSV: {str(e)}. Using default coordinates.")
        # Fallback to a minimal set of coordinates if CSV loading fails
        stations = {
            'BZA': {'name': 'Vijayawada', 'lat': 16.5167, 'lon': 80.6167},
            'GNT': {'name': 'Guntur', 'lat': 16.3067, 'lon': 80.4365},
            'VSKP': {'name': 'Visakhapatnam', 'lat': 17.6868, 'lon': 83.2185},
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

        # If selected_df is provided, use it directly as the user suggested
        if selected_df is not None and not selected_df.empty:
            # Get column names from the DataFrame
            columns = selected_df.columns.tolist()
            st.caption(f"Debug - DataFrame columns: {columns}")

            # Try to find the right column names for station code, name, latitude, and longitude
            station_code_col = next((col for col in columns if 'Station' in col and 'Code' in col), None)
            name_col = next((col for col in columns if col == 'Name'), None)
            lat_col = next((col for col in columns if 'Lat' in col), None)
            lon_col = next((col for col in columns if 'Lon' in col), None)

            # If specific columns aren't found, try to use more generic ones
            if not station_code_col:
                station_code_col = next((col for col in columns if 'Station' in col), None)
            if not name_col:
                name_col = next((col for col in columns if 'Name' in col), None)
            if not lat_col:
                lat_col = next((col for col in columns if 'lat' in col.lower()), None)
            if not lon_col:
                lon_col = next((col for col in columns if 'lon' in col.lower()), None)

            # Show the column mappings for debugging
            st.caption(f"Debug - Column mappings: Station Code={station_code_col}, Name={name_col}, Lat={lat_col}, Lon={lon_col}")

            # Add markers only for selected stations using the DataFrame directly
            for _, station in selected_df.iterrows():
                try:
                    # Get station code, name, lat, lon from the appropriate columns
                    station_code = station.get(station_code_col, '') if station_code_col else ''
                    name = station.get(name_col, '') if name_col else station_code

                    # Check if lat/lon columns exist and are valid numbers
                    if lat_col and lon_col and pd.notna(station.get(lat_col)) and pd.notna(station.get(lon_col)):
                        lat = float(station.get(lat_col))
                        lon = float(station.get(lon_col))

                        popup_content = f"""
                        <div style='font-family: Arial; font-size: 12px;'>
                            <b>{station_code} - {name}</b><br>
                            Lat: {lat:.4f}<br>
                            Lon: {lon:.4f}
                        </div>
                        """

                        folium.Marker(
                            [lat, lon],
                            popup=folium.Popup(popup_content, max_width=200),
                            tooltip=station_code,
                            icon=folium.Icon(color='red', icon='train', prefix='fa')
                        ).add_to(m)

                        # Add to points for railway line
                        selected_station_points.append([lat, lon])
                except Exception as e:
                    st.warning(f"Error adding marker for station: {e}")
        else:
            # Fallback to the old method if no DataFrame is provided
            # Create normalized lookup dictionary for case-insensitive matching
            normalized_stations = {code.upper().strip(): info for code, info in stations.items()}
            available_codes = list(normalized_stations.keys())

            # Show debugging information
            with st.expander("Debug - Station Codes"):
                st.write(f"Selected stations (raw): {selected_stations}")
                st.write(f"Available CSV station codes: {available_codes[:10]}... (total: {len(available_codes)})")

                # Create a table to show station code matching
                match_data = []
                if selected_stations:
                    for code in selected_stations:
                        normalized_code = code.upper().strip() if code else ""
                        match_data.append({
                            "Selected Code": code,
                            "Normalized Code": normalized_code,
                            "Found in CSV": normalized_code in normalized_stations,
                            "Matching Coordinates": normalized_stations.get(normalized_code, {}).get('lat', 'N/A')
                        })
                    st.table(match_data)

            # Process each selected station
            for code in selected_stations:
                if not code:
                    continue

                # Normalize the code for case-insensitive lookup
                normalized_code = code.upper().strip()

                if normalized_code in normalized_stations:
                    # Get station data from the normalized lookup
                    station_info = normalized_stations[normalized_code]
                    original_code = [k for k, v in stations.items() if k.upper().strip() == normalized_code][0]
                    station = stations[original_code]

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
                else:
                    st.warning(f"Station code '{code}' not found in coordinate data")

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
        if selected_station_points:
            st.info(f"Showing {len(selected_station_points)} of {len(selected_stations) if selected_stations else 0} selected stations on the map")