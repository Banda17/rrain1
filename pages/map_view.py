import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import os
from map_utils import OfflineMapHandler
from map_viewer import MapViewer
from PIL import ImageDraw

# Page configuration - MUST be the first Streamlit command
st.set_page_config(
    page_title="Map View - Train Tracking System",
    page_icon="🗺️",
    layout="wide"
)

# Add Bootstrap CSS to the page
st.markdown("""
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <style>
        /* Custom styles to enhance Bootstrap */
        .stApp {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        /* Add bootstrap compatible styles for Streamlit elements */
        [data-testid="stDataFrame"] table {
            border: 1px solid #dee2e6 !important;
            border-collapse: collapse !important;
            width: 100% !important;
        }
        [data-testid="stDataFrame"] th {
            background-color: #f8f9fa !important;
            border: 1px solid #dee2e6 !important;
            padding: 8px !important;
            font-weight: 600 !important;
        }
        [data-testid="stDataFrame"] td {
            border: 1px solid #dee2e6 !important;
            padding: 8px !important;
        }
        [data-testid="stDataFrame"] tr:nth-of-type(odd) {
            background-color: rgba(0,0,0,.05) !important;
        }
        [data-testid="stDataFrame"] tr:hover {
            background-color: rgba(0,0,0,.075) !important;
        }
        .station-card {
            border: 1px solid #dee2e6;
            border-radius: 0.25rem;
            padding: 0.5rem;
            margin-bottom: 0.5rem;
            background-color: #f8f9fa;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🗺️ Division Map View")
st.markdown("""
<div class="card mb-3">
    <div class="card-body">
        <p class="card-text">This interactive map shows the stations in Vijayawada Division with their GPS coordinates.
        Select stations from the table below to display them on the map.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Define Andhra Pradesh center coordinates
AP_CENTER = (16.5167, 80.6167)  # Centered around Vijayawada

# Initialize offline map handler
map_handler = OfflineMapHandler('Vijayawada_Division_System_map_page-0001 (2).png')

# Initialize map viewer for offline map
map_viewer = MapViewer()

# Station coordinates with actual GPS locations - comprehensive list
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_station_coordinates():
    """Cache station coordinates for faster access"""
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
        'PLH': {'name': 'Palasa', 'lat': 18.7726, 'lon': 84.4162},
        'GDR': {'name': 'Gudur', 'lat': 14.1487258, 'lon': 79.8456503},
        'MBL': {'name': 'Mambalam', 'lat': 14.2258343, 'lon': 79.8779689},
        'KMLP': {'name': 'Kamalpur', 'lat': 14.2258344, 'lon': 79.8779689},
        'VKT': {'name': 'Venkatagiri', 'lat': 14.3267653, 'lon': 79.9270371},
        'VDE': {'name': 'Vedayapalem', 'lat': 14.4064058, 'lon': 79.9553191},
        'NLR': {'name': 'Nellore', 'lat': 14.4530742, 'lon': 79.9868332},
        'PGU': {'name': 'Padugupadu', 'lat': 14.4980222, 'lon': 79.9901535},
        'KJJ': {'name': 'Kavali', 'lat': 14.5640002, 'lon': 79.9938934},
        'AXR': {'name': 'Allur', 'lat': 14.7101, 'lon': 79.9893},
        'BTTR': {'name': 'Bitragunta', 'lat': 14.7743359, 'lon': 79.9667298},
        'SVPM': {'name': 'Srivenkatachalapathi', 'lat': 14.7949226, 'lon': 79.9624715},
        'KVZ': {'name': 'Kovvur', 'lat': 14.9242136, 'lon': 79.9788932},
        'TTU': {'name': 'Tottaramudi', 'lat': 15.0428954, 'lon': 80.0044243},
        'UPD': {'name': 'Uppugunduru', 'lat': 15.1671213, 'lon': 80.0131329},
        'SKM': {'name': 'Singarayakonda', 'lat': 15.252886, 'lon': 80.026428},
        'OGL': {'name': 'Ongole', 'lat': 15.497849, 'lon': 80.0554939},
        'KRV': {'name': 'Karavadi', 'lat': 15.5527145, 'lon': 80.1134587},
        'ANB': {'name': 'Addanki', 'lat': 15.596741, 'lon': 80.1362815},
        'RPRL': {'name': 'Rompicherla', 'lat': 15.6171364, 'lon': 80.1677164},
        'UGD': {'name': 'Ugada', 'lat': 15.6481768, 'lon': 80.1857879},
        'KVDV': {'name': 'Kadavakollu', 'lat': 15.7164922, 'lon': 80.2369806},
        'KPLL': {'name': 'Kapileswarapuram', 'lat': 15.7482165, 'lon': 80.2573225},
        'VTM': {'name': 'Vetapalem', 'lat': 15.7797094, 'lon': 80.2739975},
        'JAQ': {'name': 'Jaggampeta', 'lat': 15.8122497, 'lon': 80.3030082},
        'CLX': {'name': 'Chirala', 'lat': 15.830938, 'lon': 80.3517708},
        'NZD': {'name': 'Vijayawada Thermal', 'lat': 16.717923, 'lon': 80.8230084},
        'VAT': {'name': 'Vijayawada Thermal', 'lat': 16.69406, 'lon': 81.0399239},
    }

# Create DataFrame for station selection
stations_df = pd.DataFrame([
    {
        'Select': False,
        'Station Code': code,
        'Name': info['name'],
        'Latitude': info['lat'],
        'Longitude': info['lon']
    }
    for code, info in get_station_coordinates().items()
])

# Create a two-column layout for table and map display with more space for the map
table_section, map_section = st.columns([2, 3], gap="small")

with table_section:
    st.markdown("""
    <div class="card mb-3">
        <div class="card-header bg-primary text-white">
            Station Selection
        </div>
""", unsafe_allow_html=True)
    # Create a column layout to control table width
    table_col1, table_col2 = st.columns([3, 1])
    with table_col1:
        # Make the dataframe interactive with checkboxes - with enhanced Bootstrap styling
        st.markdown('<div class="card-body p-0">', unsafe_allow_html=True)
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
            disabled=["Station Code", "Name", "Latitude", "Longitude"],
            use_container_width=False,
            height=800,  # Increased height further
            num_rows=40  # Show 40 rows at a time
        )

        # Add table footer with selection count
        selected_count = len(edited_df[edited_df['Select']])
        st.markdown(f'<div class="card-footer bg-light d-flex justify-content-between"><span>Total Stations: {len(stations_df)}</span><span>Selected: {selected_count}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with table_col2:
        # Empty space to reduce table width
        st.empty()

with map_section:
    # Get selected stations
    selected_stations = edited_df[edited_df['Select']]

    # First, set a default map type value to use
    if 'map_type' not in st.session_state:
        st.session_state['map_type'] = "Offline Map with GPS Markers"

    # Display the appropriate map based on the current map type
    if st.session_state['map_type'] == "Offline Map with GPS Markers":
        # Function to render offline map with markers
        def render_offline_map_with_markers(selected_stations_df):
            """Render an offline map with GPS markers for selected stations"""
            # Temporarily increase marker size
            original_marker_size = map_viewer.base_marker_size
            map_viewer.base_marker_size = 25  # Increased from default 15 to 25

            # Load the base map
            base_map = map_viewer.load_map()
            if base_map is None:
                # Restore original marker size before returning
                map_viewer.base_marker_size = original_marker_size
                return None, []

            # Create a copy of the base map to draw on
            display_image = base_map.copy()

            # First, draw small dots for all non-selected stations
            draw = ImageDraw.Draw(display_image)

            # Get all station coordinates
            station_coords = get_station_coordinates()

            # Create a list of selected station codes for easy lookup
            selected_codes = [row['Station Code'].upper().strip() for _, row in selected_stations_df.iterrows()]

            # Draw small dots for all non-selected stations
            for code, info in station_coords.items():
                # Skip if this is a selected station (will be drawn with a marker later)
                if code in selected_codes:
                    continue

                # Try to convert GPS coordinates to map coordinates
                try:
                    # Approximate conversion
                    x_norm = (info['lon'] - 79.0) / 5.0
                    y_norm = (info['lat'] - 14.0) / 5.0

                    # Add to map_viewer's station locations for future use
                    map_viewer.station_locations[code] = {
                        'x': x_norm,
                        'y': y_norm
                    }

                    # Convert normalized coordinates to pixel coordinates
                    width, height = display_image.size
                    x = int(x_norm * width)
                    y = int(y_norm * height)

                    # Draw a small dot
                    dot_radius = 5
                    draw.ellipse((x-dot_radius, y-dot_radius, x+dot_radius, y+dot_radius), 
                                fill=(100, 100, 100, 180))  # Gray with some transparency
                except:
                    # Skip if conversion fails
                    continue

            # Keep track of displayed stations
            displayed_stations = []

            # Draw markers for each selected station
            for _, station in selected_stations_df.iterrows():
                code = station['Station Code']
                normalized_code = code.upper().strip()

                # Try to add using map_viewer first
                if normalized_code in map_viewer.station_locations:
                    display_image = map_viewer.draw_train_marker(display_image, normalized_code)
                    displayed_stations.append(normalized_code)
                else:
                    # Convert GPS coordinates to approximate map coordinates
                    lat, lon = station['Latitude'], station['Longitude']

                    # Add to map_viewer's station locations (temporary)
                    map_viewer.station_locations[normalized_code] = {
                        'x': (lon - 79.0) / 5.0,  # Approximate conversion
                        'y': (lat - 14.0) / 5.0   # Approximate conversion
                    }

                    # Draw the marker
                    display_image = map_viewer.draw_train_marker(display_image, normalized_code)
                    displayed_stations.append(normalized_code)

            # Restore original marker size
            map_viewer.base_marker_size = original_marker_size

            return display_image, displayed_stations

        # Use the function to render offline map with markers
        display_image, displayed_stations = None, []

        # Always render the map to show all stations as dots
        display_image, displayed_stations = render_offline_map_with_markers(selected_stations)

        if display_image is not None:
            # Resize for display if needed
            from PIL import Image
            original_width, original_height = display_image.size
            max_height = 650  # Increased height
            height_ratio = max_height / original_height
            new_width = int(original_width * height_ratio * 1.2)  # Extra width factor

            # Card container for the map
            st.markdown("""
            <div class="card mb-3">
                <div class="card-header bg-secondary text-white">
                    Vijayawada Division System Map
                </div>
                <div class="card-body p-0">
            """, unsafe_allow_html=True)

            # Display the map
            st.image(
                display_image.resize((new_width, max_height)), #resize image
                use_container_width=True,
                caption="Vijayawada Division System Map with Selected Stations"
            )

            st.markdown("</div></div>", unsafe_allow_html=True)

            # Show station count
            if displayed_stations:
                st.success(f"Showing {len(displayed_stations)} selected stations with markers and all other stations as dots")
            else:
                st.info("No stations selected. All stations shown as dots on the map.")
        else:
            st.error("Unable to load the offline map. Please check the map file.")
    else:  # Interactive GPS Map
        # Create the map
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

        # Get all station coordinates
        station_coords = get_station_coordinates()

        # Create a list of selected station codes for easy lookup
        selected_codes = [row['Station Code'].upper().strip() for _, row in selected_stations.iterrows()]

        # First add small dots for all non-selected stations
        for code, info in station_coords.items():
            # Skip if this is a selected station (will be drawn with a marker later)
            if code.upper() in selected_codes:
                continue

            # Calculate position offsets for label placement
            x_offset = 10
            y_offset = -10

            # Add box around dot with label with custom positioning
            # Remove the arrow and make sizing consistent regardless of zoom
            html_content = f'''
            <div style="position:absolute; width:0; height:0;">
                <!-- Box around station location -->
                <div style="position:absolute; width:6px; height:6px; border:1px solid #800000; left:-3px; top:-3px; border-radius:1px; background-color:rgba(255,255,255,0.5);"></div>
                <!-- Station label -->
                <div style="position:absolute; left:{10 if x_offset < 0 else -40}px; top:{-18 if y_offset < 0 else 0}px; background-color:rgba(255,255,255,0.8); padding:1px 3px; border:1px solid #800000; border-radius:2px; font-size:9px; white-space:nowrap;">{code}</div>
            </div>
            '''

            folium.DivIcon(
                icon_size=(0, 0),  # Using zero size to improve positioning
                icon_anchor=(0, 0),  # Centered anchor point
                html=html_content
            ).add_to(folium.Marker(
                [info['lat'], info['lon']],
                icon=folium.DivIcon(icon_size=(0, 0))  # Invisible marker
            ).add_to(m))

        # Add markers only for selected stations
        if not selected_stations.empty:
            # Add markers for selected stations
            valid_points = []
            for _, station in selected_stations.iterrows():
                code = station['Station Code']
                lat, lon = station['Latitude'], station['Longitude']

                # Calculate position offsets for label placement
                x_offset = 10
                y_offset = -10

                # Add box around dot with label - remove arrow and make sizing consistent
                html_content = f'''
                <div style="position:absolute; width:0; height:0;">
                    <!-- Larger box for selected station -->
                    <div style="position:absolute; width:8px; height:8px; border:2px solid #800000; left:-4px; top:-4px; border-radius:2px; background-color:rgba(255,255,255,0.5);"></div>
                    <!-- Prominent station label -->
                    <div style="position:absolute; left:{15 if x_offset < 0 else -50}px; top:{-20 if y_offset < 0 else 0}px; background-color:rgba(255,255,255,0.9); padding:2px 4px; border:2px solid #800000; border-radius:3px; font-weight:bold; font-size:10px; color:#800000; white-space:nowrap;">{code}</div>
                </div>
                '''

                folium.DivIcon(
                    icon_size=(0, 0),  # Using zero size to improve positioning
                    icon_anchor=(0, 0),  # Centered anchor point
                    html=html_content
                ).add_to(folium.Marker(
                    [lat, lon],
                    icon=folium.DivIcon(icon_size=(0, 0))
                ).add_to(m))

                # Add to points for railway line
                valid_points.append([lat, lon])

            # Add railway lines between selected stations
            if len(valid_points) > 1:
                folium.PolyLine(
                    valid_points,
                    weight=2,
                    color='gray',
                    opacity=0.8,
                    dash_array='5, 10'
                ).add_to(m)

        # Card container for the map
        st.markdown("""
        <div class="card mb-3">
            <div class="card-header bg-secondary text-white">
                Interactive GPS Map
            </div>
            <div class="card-body p-0">
        """, unsafe_allow_html=True)

        # Display the map with increased width
        folium_static(m, width=900, height=650)

        st.markdown("</div></div>", unsafe_allow_html=True)

    # Add a separator to separate the map from the radio buttons
    st.markdown("---")

    # Display the map type selection radio buttons below the map
    selected_map_type = st.radio(
        "Map Type", 
        ["Offline Map with GPS Markers", "Interactive GPS Map"],
        index=0 if st.session_state['map_type'] == "Offline Map with GPS Markers" else 1, 
        horizontal=True,
        key="map_type_selector"
    )

    # Update the session state when the selection changes
    if selected_map_type != st.session_state['map_type']:
        st.session_state['map_type'] = selected_map_type
        st.rerun()  # Refresh to apply the new map type

# Add instructions in collapsible section
with st.expander("About GPS Coordinates"):
    st.markdown("""
    <div class="card">
        <div class="card-header bg-light">
            GPS Coordinate System
        </div>
        <div class="card-body">
            <ul class="list-group list-group-flush">
                <li class="list-group-item">Latitude: North-South position (-90° to 90°)</li>
                <li class="list-group-item">Longitude: East-West position (-180° to 180°)</li>
                <li class="list-group-item">Coordinates shown are in decimal degrees format</li>
            </ul>
        </div>
        <div class="card-header bg-light">
            Map Features
        </div>
        <div class="card-body">
            <ul class="list-group list-group-flush">
                <li class="list-group-item">Switch between offline map and interactive GPS view</li>
                <li class="list-group-item">Railway lines automatically connect selected stations in sequence</li>
                <li class="list-group-item">All stations shown as small dots, selected stations shown with train markers</li>
                <li class="list-group-item">Select multiple stations to see their connections</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)