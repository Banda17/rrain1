import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import os
from map_utils import OfflineMapHandler
from map_viewer import MapViewer
from PIL import ImageDraw

# Page configuration
st.set_page_config(
    page_title="Map View - Train Tracking System",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Division Map View")
st.markdown("""
This interactive map shows the stations in Vijayawada Division with their GPS coordinates.
Select stations from the table below to display them on the map.
""")

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
        'NZD': {'name': 'Nidubrolu', 'lat': 16.717923, 'lon': 80.8230084},
        'VAT': {'name': 'Vijayawada Thermal', 'lat': 16.69406, 'lon': 81.0399239},
    }

# Apply custom CSS to remove all padding and margins between columns
st.markdown("""
<style>
.stColumn > div {
    padding: 0px !important;
}
div[data-testid="column"] {
    padding: 0px !important;
    margin: 0px !important;
}
.block-container {
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
    max-width: 100% !important;
}
div[data-testid="stVerticalBlock"] {
    gap: 0px !important;
}
/* Custom styling to make table wider */
[data-testid="stDataFrame"] {
    width: 100% !important;
    max-width: none !important;
}
</style>
""", unsafe_allow_html=True)

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
# Use more table space, 60% table to 40% map ratio
table_section, map_section = st.columns([2, 3], gap="small")

with table_section:
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
        disabled=["Station Code", "Name", "Latitude", "Longitude"],
        use_container_width=True,  # Make table fill the available width
        height=800,  # Increased height further
        num_rows=40  # Show 40 rows at a time
    )

with map_section:
    # Remove extra padding/margin to bring map closer to table
    st.markdown("""
    <style>
    .stColumn > div:first-child {
        padding-left: 0 !important;
        margin-left: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Get selected stations
    selected_stations = edited_df[edited_df['Select']]

    # Store the current map type in session state if not already present
    if 'current_map_type' not in st.session_state:
        st.session_state.current_map_type = "Offline Map with GPS Markers"

    # Display maps - now we'll display both and control visibility with CSS
    # First, prepare both maps but only render the selected one

    # OFFLINE MAP SECTION
    st.markdown('<div id="offline-map-container">', unsafe_allow_html=True)

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
                draw.ellipse((x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius),
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
                    'y': (lat - 14.0) / 5.0  # Approximate conversion
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

    # Display the offline map (will be controlled by visibility)
    if display_image is not None:
        # Resize for display if needed
        from PIL import Image
        original_width, original_height = display_image.size
        max_height = 650  # Increased height
        height_ratio = max_height / original_height
        new_width = int(original_width * height_ratio * 1.2)  # Extra width factor

        # Display the map
        st.image(
            display_image.resize((new_width, max_height)),  # resize image
            use_container_width=True,
            caption="Vijayawada Division System Map with Selected Stations"
        )

        # Show station count
        if displayed_stations:
            st.success(f"Showing {len(displayed_stations)} selected stations with markers and all other stations as dots")
        else:
            st.info("No stations selected. All stations shown as dots on the map.")
    else:
        st.error("Unable to load the offline map. Please check the map file.")

    st.markdown('</div>', unsafe_allow_html=True)

    # INTERACTIVE GPS MAP SECTION
    st.markdown('<div id="interactive-map-container">', unsafe_allow_html=True)

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

    # Get all station coordinates
    station_coords = get_station_coordinates()

    # Create a list of selected station codes for easy lookup
    selected_codes = [row['Station Code'].upper().strip() for _, row in selected_stations.iterrows()]

    # Create a counter to alternate label positions
    counter = 0

    # First add small dots for all non-selected stations
    for code, info in station_coords.items():
        # Skip if this is a selected station (will be drawn with a marker later)
        if code.upper() in selected_codes:
            continue

        # Determine offset for alternating left/right positioning
        x_offset = -50 if counter % 2 == 0 else 50  # Pixels left or right
        y_offset = 0  # No vertical offset

        # Every 3rd station, use vertical offset instead to further reduce overlap
        if counter % 3 == 0:
            x_offset = 0
            y_offset = -30  # Above the point

        counter += 1

        # Add small circle marker for the station with maroon border
        folium.CircleMarker(
            [info['lat'], info['lon']],
            radius=3,  # Small radius
            color='#800000',  # Maroon red border
            fill=True,
            fill_color='gray',
            fill_opacity=0.6,
            opacity=0.8,
            tooltip=code
        ).add_to(m)

        # Determine arrow direction based on offset
        arrow_direction = "←" if x_offset > 0 else "→"
        if y_offset < 0:
            arrow_direction = "↓"

        # Add box around dot with arrow and label with custom positioning
        # Make sizing consistent regardless of zoom by using absolute elements
        html_content = f'''
        <div style="position:absolute; width:0; height:0;">
            <!-- Box around station location -->
            <div style="position:absolute; width:6px; height:6px; border:1px solid #800000; left:-3px; top:-3px; border-radius:1px; background-color:rgba(255,255,255,0.5);"></div>
            <!-- Arrow pointing to station -->
            <div style="position:absolute; left:{2 if x_offset < 0 else -8}px; top:{-2 if y_offset < 0 else 0}px; color:#800000; font-size:12px; font-weight:bold; line-height:1;">{arrow_direction}</div>
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
            lat = station['Latitude']
            lon = station['Longitude']

            # Determine offset for selected stations - opposite to non-selected pattern
            x_offset = 50 if counter % 2 == 0 else -50
            y_offset = -30 if counter % 3 == 0 else 0
            counter += 1

            # Create custom popup content
            popup_content = f"""
            <div style='font-family: Arial; font-size: 12px;'>
                <b>{code} - {station['Name']}</b><br>
                Lat: {lat:.4f}<br>
                Lon: {lon:.4f}
            </div>
            """

            # Add train icon marker
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup_content, max_width=200),
                tooltip=code,
                icon=folium.Icon(color='red', icon='train', prefix='fa'),
                opacity=0.9  # Fixed opacity
            ).add_to(m)

            # Determine arrow direction based on offset
            arrow_direction = "←" if x_offset > 0 else "→"
            if y_offset < 0:
                arrow_direction = "↓"

            # Add highlighted box, arrow, and prominent label with zoom-stable positioning
            html_content = f'''
            <div style="position:absolute; width:0; height:0;">
                <!-- Larger box for selected station -->
                <div style="position:absolute; width:8px; height:8px; border:2px solid #800000; left:-4px; top:-4px; border-radius:2px; background-color:rgba(255,255,255,0.5);"></div>
                <!-- Bold arrow -->
                <div style="position:absolute; left:{5 if x_offset < 0 else -15}px; top:{-3 if y_offset < 0 else 0}px; color:#800000; font-size:14px; font-weight:bold; line-height:1;">{arrow_direction}</div>
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
                opacity=0.8,  # Fixed opacity
                dash_array='5, 10'
            ).add_to(m)

    # Display the interactive map
    st.subheader("Interactive Map")
    folium_static(m, width=1300, height=650)

    st.markdown('</div>', unsafe_allow_html=True)

    # Add some visual separation before the map type selection
    st.markdown("""
    <div style="margin-top: 20px; margin-bottom: 20px; border-top: 1px solid #e6e6e6; padding-top: 10px;"></div>
    """, unsafe_allow_html=True)

    # Add Map Type Selection BELOW both maps
    map_type = st.radio("Map Type", ["Offline Map with GPS Markers", "Interactive GPS Map"],
                     index=0 if st.session_state.current_map_type == "Offline Map with GPS Markers" else 1, 
                     horizontal=True)

    # Update the session state when selection changes
    if map_type != st.session_state.current_map_type:
        st.session_state.current_map_type = map_type
        st.rerun()  # Rerun the app to update the map display

    # Add CSS to control map visibility based on selection
    visibility_css = f"""
    <style>
    #{'offline-map-container' if map_type == 'Offline Map with GPS Markers' else 'interactive-map-container'} {{
        display: block;
    }}
    #{'interactive-map-container' if map_type == 'Offline Map with GPS Markers' else 'offline-map-container'} {{
        display: none;
    }}
    </style>
    """
    st.markdown(visibility_css, unsafe_allow_html=True)

# Add instructions in collapsible section
with st.expander("About GPS Coordinates"):
    st.markdown("""
    ### GPS Coordinate System
    - **Latitude**: North-South position (-90° to 90°)
    - **Longitude**: East-West position (-180° to 180°)
    - Coordinates shown are in decimal degrees format

    ### Map Features
    - Switch between offline map and interactive GPS view
    - Railway lines automatically connect selected stations in sequence
    - All stations shown as small dots, selected stations shown with train markers
    - Select multiple stations to see their connections
    """)