import streamlit as st
from map_viewer import MapViewer
from PIL import Image, ImageDraw, ImageFont
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Map View - Train Tracking System",
    page_icon="🗺️",
    layout="wide"
)

# Initialize map viewer
map_viewer = MapViewer()

st.title("🗺️ Division Map View")
st.markdown("""
This interactive map shows the stations in Vijayawada Division with their GPS coordinates.
Use the controls below to customize the view.
""")

# Controls
col1, col2 = st.columns([1, 2])
with col1:
    show_coords = st.checkbox("Show GPS Coordinates", value=True)
    show_station_list = st.checkbox("Show Station List", value=True)
    route_filter = st.selectbox(
        "Filter by Route",
        ["All Stations", "Vijayawada-Gudur", "Thadi-Vijayawada"],
        index=0
    )

# Create a DataFrame of stations with route information
def get_route_for_station(coords):
    # Simplified route determination based on coordinates
    if 0.10 <= coords['x'] <= 0.50 and 0.55 <= coords['y'] <= 0.60:
        return "Thadi-Vijayawada"
    else:
        return "Vijayawada-Gudur"

stations_df = pd.DataFrame([
    {
        'Station Code': code,
        'GPS Coordinates': f"({coords['x']:.4f}, {coords['y']:.4f})",
        'Route': get_route_for_station(coords)
    }
    for code, coords in map_viewer.station_locations.items()
])

# Apply route filter
if route_filter != "All Stations":
    stations_df = stations_df[stations_df['Route'] == route_filter]

# Load and prepare the base map
base_map = map_viewer.load_map()

if base_map:
    # Draw all station markers
    display_image = base_map.copy()

    # Only draw markers for filtered stations
    for _, row in stations_df.iterrows():
        display_image = map_viewer.draw_train_marker(
            display_image, 
            row['Station Code']
        )

    # Convert and resize for display
    display_image = display_image.convert('RGB')
    original_width, original_height = display_image.size

    # Calculate new dimensions maintaining aspect ratio
    max_height = 600  # Larger height for better visibility
    height_ratio = max_height / original_height
    new_width = int(original_width * height_ratio * 1.2)
    new_height = max_height

    display_image = display_image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS
    )

    # Display the map
    st.image(
        display_image,
        use_container_width=True,
        caption=f"Station Markers on Vijayawada Division System Map ({route_filter})"
    )

    # Show station list if enabled
    if show_station_list:
        st.subheader("Station Coordinates")

        # Allow sorting by any column
        sort_by = st.selectbox("Sort by", stations_df.columns.tolist())
        stations_df_sorted = stations_df.sort_values(sort_by)

        if show_coords:
            st.dataframe(
                stations_df_sorted,
                use_container_width=True,
                height=400
            )
        else:
            st.dataframe(
                stations_df_sorted[['Station Code', 'Route']],
                use_container_width=True,
                height=400
            )

        # Show station count
        st.info(f"Showing {len(stations_df)} stations" + 
                (f" on {route_filter} route" if route_filter != "All Stations" else ""))
else:
    st.error("Unable to load the base map. Please check the map file path.")

# Add description of coordinate system
st.markdown("""
### About the Coordinate System
- Coordinates are normalized to the range (0,0) to (1,1)
- X: Horizontal position (0 = leftmost, 1 = rightmost)
- Y: Vertical position (0 = topmost, 1 = bottommost)
""")