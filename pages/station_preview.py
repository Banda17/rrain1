import streamlit as st
from map_viewer import MapViewer
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import re

# Page configuration
st.set_page_config(
    page_title="Station Markers Preview",
    page_icon="📍",
    layout="wide"
)

# Initialize map viewer
map_viewer = MapViewer()

st.title("📍 Station Markers Preview")
st.markdown("This page shows all station locations on the map. Edit coordinates in the table below to adjust station positions.")

# Controls
show_coords = st.checkbox("Show Coordinates", value=True)

# Create a DataFrame of stations for easy display and editing
stations_df = pd.DataFrame([
    {
        'Station Code': code,
        'X Coordinate': coords['x'],
        'Y Coordinate': coords['y']
    }
    for code, coords in map_viewer.station_locations.items()
])

def update_map_viewer_file(updated_coords):
    """Update the map_viewer.py file with new coordinates"""
    try:
        with open('map_viewer.py', 'r') as file:
            content = file.read()

        # Find the station_locations dictionary in the file
        start_pattern = r"self\.station_locations = {"
        match = re.search(start_pattern, content)
        if not match:
            st.error("Could not find station locations in map_viewer.py")
            return False

        # Build the new station locations dictionary
        new_dict = "        self.station_locations = {\n"
        for code, coords in updated_coords.items():
            new_dict += f"            '{code}': {{\n"
            new_dict += f"                'x': {coords['x']:.2f},\n"
            new_dict += f"                'y': {coords['y']:.2f}\n"
            new_dict += "            },\n"
        new_dict += "        }"

        # Replace the old dictionary with the new one
        pattern = r"self\.station_locations = \{[^}]+\}"
        updated_content = re.sub(pattern, new_dict.rstrip(',\n') + "}", content, flags=re.DOTALL)

        # Write the updated content back to the file
        with open('map_viewer.py', 'w') as file:
            file.write(updated_content)

        return True

    except Exception as e:
        st.error(f"Error updating map_viewer.py: {str(e)}")
        return False

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

    # Show editable station list
    st.subheader("Station Coordinates")
    st.markdown("Edit the X and Y coordinates below to adjust station positions (values between 0 and 1)")

    # Make the dataframe editable
    edited_df = st.data_editor(
        stations_df,
        use_container_width=True,
        height=400,
        column_config={
            "Station Code": st.column_config.TextColumn(
                "Station Code",
                help="Station identification code",
                width="medium",
                required=True
            ),
            "X Coordinate": st.column_config.NumberColumn(
                "X Coordinate",
                help="Horizontal position (0-1)",
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                format="%.2f"
            ),
            "Y Coordinate": st.column_config.NumberColumn(
                "Y Coordinate",
                help="Vertical position (0-1)",
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                format="%.2f"
            )
        },
        disabled=["Station Code"],
        num_rows="dynamic"
    )

    # Update map_viewer's station locations if coordinates have changed
    if edited_df is not None and not edited_df.equals(stations_df):
        # Update the in-memory coordinates
        updated_coords = {}
        for _, row in edited_df.iterrows():
            station_code = row['Station Code']
            map_viewer.station_locations[station_code] = {
                'x': row['X Coordinate'],
                'y': row['Y Coordinate']
            }
            updated_coords[station_code] = {
                'x': row['X Coordinate'],
                'y': row['Y Coordinate']
            }

        # Update the file
        if update_map_viewer_file(map_viewer.station_locations):
            st.success("Coordinates updated in map_viewer.py! The changes will be reflected on the map above.")

        # Add a button to reset coordinates to default
        if st.button("Reset to Default Coordinates"):
            st.rerun()
else:
    st.error("Unable to load the base map. Please check the map file path.")