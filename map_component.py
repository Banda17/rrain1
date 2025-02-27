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
    # Hardcoded station coordinates extracted from the CSV file
    stations = {
        'GDR': {'name': 'GDR', 'lat': 14.1487258, 'lon': 79.8456503},
        'MBL': {'name': 'MBL', 'lat': 14.2258343, 'lon': 79.8779689},
        'KMLP': {'name': 'KMLP', 'lat': 14.2258344, 'lon': 79.8779689},
        'VKT': {'name': 'VKT', 'lat': 14.3267653, 'lon': 79.9270371},
        'VDE': {'name': 'VDE', 'lat': 14.4064058, 'lon': 79.9553191},
        'NLR': {'name': 'NLR', 'lat': 14.4530742, 'lon': 79.9868332},
        'PGU': {'name': 'PGU', 'lat': 14.4980222, 'lon': 79.9901535},
        'KJJ': {'name': 'KJJ', 'lat': 14.5640002, 'lon': 79.9938934},
        'AXR': {'name': 'AXR', 'lat': 14.7101, 'lon': 79.9893},
        'BTTR': {'name': 'BTTR', 'lat': 14.7743359, 'lon': 79.9667298},
        'SVPM': {'name': 'SVPM', 'lat': 14.7949226, 'lon': 79.9624715},
        'KVZ': {'name': 'KVZ', 'lat': 14.9242136, 'lon': 79.9788932},
        'TTU': {'name': 'TTU', 'lat': 15.0428954, 'lon': 80.0044243},
        'UPD': {'name': 'UPD', 'lat': 15.1671213, 'lon': 80.0131329},
        'SKM': {'name': 'SKM', 'lat': 15.252886, 'lon': 80.026428},
        'OGL': {'name': 'OGL', 'lat': 15.497849, 'lon': 80.0554939},
        'KRV': {'name': 'KRV', 'lat': 15.5527145, 'lon': 80.1134587},
        'ANB': {'name': 'ANB', 'lat': 15.596741, 'lon': 80.1362815},
        'RPRL': {'name': 'RPRL', 'lat': 15.6171364, 'lon': 80.1677164},
        'UGD': {'name': 'UGD', 'lat': 15.6481768, 'lon': 80.1857879},
        'KVDV': {'name': 'KVDV', 'lat': 15.7164922, 'lon': 80.2369806},
        'KPLL': {'name': 'KPLL', 'lat': 15.7482165, 'lon': 80.2573225},
        'VTM': {'name': 'VTM', 'lat': 15.7797094, 'lon': 80.2739975},
        'JAQ': {'name': 'JAQ', 'lat': 15.8122497, 'lon': 80.3030082},
        'CLX': {'name': 'CLX', 'lat': 15.830938, 'lon': 80.3517708},
        'IPPM': {'name': 'IPPM', 'lat': 15.85281, 'lon': 80.3814662},
        'SPF': {'name': 'SPF', 'lat': 15.8752985, 'lon': 80.4140117},
        'BPP': {'name': 'BPP', 'lat': 15.9087804, 'lon': 80.4652035},
        'APL': {'name': 'APL', 'lat': 15.9703661, 'lon': 80.5142194},
        'MCVM': {'name': 'MCVM', 'lat': 16.0251057, 'lon': 80.5391888},
        'NDO': {'name': 'NDO', 'lat': 16.0673498, 'lon': 80.5553901},
        'MDKU': {'name': 'MDKU', 'lat': 16.1233333, 'lon': 80.5799375},
        'TSR': {'name': 'TSR', 'lat': 16.1567184, 'lon': 80.5832601},
        'TEL': {'name': 'TEL', 'lat': 16.2435852, 'lon': 80.6376458},
        'KLX': {'name': 'KLX', 'lat': 16.2946856, 'lon': 80.6260305},
        'DIG': {'name': 'DIG', 'lat': 16.329159, 'lon': 80.6232471},
        'CLVR': {'name': 'CLVR', 'lat': 16.3802036, 'lon': 80.6164899},
        'PVD': {'name': 'PVD', 'lat': 16.4150823, 'lon': 80.6107384},
        'KCC': {'name': 'KCC', 'lat': 16.4778294, 'lon': 80.600124},
        'BZA': {'name': 'BZA', 'lat': 16.5186803, 'lon': 80.5787723},
        'VNEC': {'name': 'VNEC', 'lat': 16.5315126, 'lon': 80.6256334},
        'GALA': {'name': 'GALA', 'lat': 16.5378371, 'lon': 80.6731917},
        'MBD': {'name': 'MBD', 'lat': 16.554087, 'lon': 80.7036966},
        'GWM': {'name': 'GWM', 'lat': 16.5562972, 'lon': 80.7933824},
        'PAVP': {'name': 'PAVP', 'lat': 16.5626982, 'lon': 80.8033418},
        'TOU': {'name': 'TOU', 'lat': 16.5989042, 'lon': 80.8815233},
        'NZD': {'name': 'NZD', 'lat': 16.717923, 'lon': 80.8230084},
        'VAT': {'name': 'VAT', 'lat': 16.69406, 'lon': 81.0399239},
        'PRH': {'name': 'PRH', 'lat': 16.7132558, 'lon': 81.1025796},
        'EE': {'name': 'EE', 'lat': 16.7132548, 'lon': 81.0845549},
        'DEL': {'name': 'DEL', 'lat': 16.7818664, 'lon': 81.1780754},
        'BMD': {'name': 'BMD', 'lat': 16.818151, 'lon': 81.2627899},
        'PUA': {'name': 'PUA', 'lat': 16.8096519, 'lon': 81.3207946},
        'CEL': {'name': 'CEL', 'lat': 16.8213153, 'lon': 81.3900847},
        'BPY': {'name': 'BPY', 'lat': 16.8279598, 'lon': 81.4719773},
        'TDD': {'name': 'TDD', 'lat': 16.8067368, 'lon': 81.52052},
        'NBM': {'name': 'NBM', 'lat': 16.83, 'lon': 81.5922511},
        'NDD': {'name': 'NDD', 'lat': 16.8959685, 'lon': 81.6728381},
        'CU': {'name': 'CU', 'lat': 16.9702728, 'lon': 81.686414},
        'PSDA': {'name': 'PSDA', 'lat': 16.9888598, 'lon': 81.6959144},
        'KVR': {'name': 'KVR', 'lat': 17.003964, 'lon': 81.7217881},
        'GVN': {'name': 'GVN', 'lat': 17.0050447, 'lon': 81.7683895},
        'RJY': {'name': 'RJY', 'lat': 16.9841444, 'lon': 81.7835278},
        'KYM': {'name': 'KYM', 'lat': 16.9135426, 'lon': 81.8291201},
        'DWP': {'name': 'DWP', 'lat': 16.9264801, 'lon': 81.9185066},
        'APT': {'name': 'APT', 'lat': 16.9353876, 'lon': 81.9510518},
        'BVL': {'name': 'BVL', 'lat': 16.967466, 'lon': 82.0283906},
        'MPU': {'name': 'MPU', 'lat': 17.0050166, 'lon': 82.0930538},
        'SLO': {'name': 'SLO', 'lat': 17.0473849, 'lon': 82.1652452},
        'PAP': {'name': 'PAP', 'lat': 17.1127264, 'lon': 82.2560612},
        'GLP': {'name': 'GLP', 'lat': 17.1544365, 'lon': 82.2873605},
        'DGDG': {'name': 'DGDG', 'lat': 17.2108602, 'lon': 82.3447996},
        'RVD': {'name': 'RVD', 'lat': 17.2280704, 'lon': 82.3631186},
        'ANV': {'name': 'ANV', 'lat': 17.2689997, 'lon': 82.4142117},
        'HVM': {'name': 'HVM', 'lat': 17.3127808, 'lon': 82.485711},
        'TUNI': {'name': 'TUNI', 'lat': 17.3611943, 'lon': 82.5421967},
        'GLU': {'name': 'GLU', 'lat': 17.4098079, 'lon': 82.6294254},
        'NRP': {'name': 'NRP', 'lat': 17.4511567, 'lon': 82.7188935},
        'REG': {'name': 'REG', 'lat': 17.5052679, 'lon': 82.7880359},
        'YLM': {'name': 'YLM', 'lat': 17.5534876, 'lon': 82.8428433},
        'NASP': {'name': 'NASP', 'lat': 17.6057255, 'lon': 82.8899697},
        'BVM': {'name': 'BVM', 'lat': 17.6600783, 'lon': 82.9259044},
        'KSK': {'name': 'KSK', 'lat': 17.6732113, 'lon': 82.9564764},
        'AKP': {'name': 'AKP', 'lat': 17.6934772, 'lon': 83.0049398},
        'THY': {'name': 'THY', 'lat': 17.6865433, 'lon': 83.0665228},
        'DVD': {'name': 'DVD', 'lat': 17.7030476, 'lon': 83.1485371},
        # Additional key stations
        'VSKP': {'name': 'Visakhapatnam', 'lat': 17.6868, 'lon': 83.2185},
        'GNT': {'name': 'Guntur', 'lat': 16.3067, 'lon': 80.4365},
        'NLDA': {'name': 'Nalgonda', 'lat': 17.0575, 'lon': 79.2690},
        'MTM': {'name': 'Mangalagiri', 'lat': 16.4307, 'lon': 80.5525},
        'NDL': {'name': 'Nidadavolu', 'lat': 16.9107, 'lon': 81.6717},
        'VZM': {'name': 'Vizianagaram', 'lat': 18.1066, 'lon': 83.4205},
        'PLH': {'name': 'Palasa', 'lat': 18.7726, 'lon': 84.4162}
    }

    # Attempt to load additional stations from CSV as a backup
    try:
        station_df = pd.read_csv('attached_assets/station_coordinates (1).csv')
        # Add any stations from CSV that aren't already in the hardcoded list
        for _, row in station_df.iterrows():
            if not pd.isna(row['Station']) and not pd.isna(row['Latitude']) and not pd.isna(row['Longitude']):
                station_code = row['Station']
                if station_code not in stations:
                    stations[station_code] = {
                        'name': station_code,
                        'lat': float(row['Latitude']),
                        'lon': float(row['Longitude'])
                    }
    except Exception as e:
        # Just use hardcoded values if CSV fails
        pass

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
            # Process each selected station
            for code in selected_stations:
                if not code:
                    continue

                # Normalize the code for case-insensitive lookup
                normalized_code = code.upper().strip()

                # First try direct lookup
                if code in stations:
                    station = stations[code]
                # Then try normalized lookup
                elif normalized_code in stations:
                    station = stations[normalized_code]
                # Try case-insensitive lookup in all keys
                else:
                    matching_codes = [k for k in stations.keys() if k.upper().strip() == normalized_code]
                    if matching_codes:
                        station = stations[matching_codes[0]]
                    else:
                        st.warning(f"Station code '{code}' not found in coordinate data")
                        continue

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
        if selected_station_points:
            st.info(f"Showing {len(selected_station_points)} of {len(selected_stations) if selected_stations else 0} selected stations on the map")