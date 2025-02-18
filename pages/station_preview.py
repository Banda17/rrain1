import streamlit as st
from map_viewer import MapViewer
from PIL import Image, ImageDraw, ImageFont
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Station Markers Preview",
    page_icon="📍",
    layout="wide"
)

# Initialize map viewer
map_viewer = MapViewer()

st.title("📍 Station Markers Preview")
st.markdown("This page shows all station locations on the map")

# Controls
show_coords = st.checkbox("Show Coordinates", value=True)
show_station_list = st.checkbox("Show Station List", value=True)

# Create a DataFrame of stations for easy display
stations_df = pd.DataFrame([
    {
        'Station Code': code,
        'X Coordinate': coords['x'],
        'Y Coordinate': coords['y']
    }
    for code, coords in map_viewer.station_locations.items()
])

# Load and prepare the base map
base_map = map_viewer.load_map()

if base_map:
    # Draw all station markers
    display_image = base_map.copy()
    
    for station_code in map_viewer.station_locations.keys():
        display_image = map_viewer.draw_train_marker(display_image, station_code)
    
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
        caption="Station Markers on Vijayawada Division System Map"
    )
    
    # Show station list if enabled
    if show_station_list:
        st.subheader("Station List")
        if show_coords:
            st.dataframe(
                stations_df.sort_values('Station Code'),
                use_container_width=True,
                height=400
            )
        else:
            st.dataframe(
                stations_df[['Station Code']].sort_values('Station Code'),
                use_container_width=True,
                height=400
            )
else:
    st.error("Unable to load the base map. Please check the map file path.")
