import streamlit as st
from PIL import Image, ImageDraw
from typing import Dict, Optional, Tuple

class MapViewer:
    def __init__(self):
        # Station coordinates (normalized to image coordinates)
        self.station_locations = {
            'VNEC': {'x': 0.7, 'y': 0.3},   # Secunderabad
            'GALA': {'x': 0.65, 'y': 0.35},  # Gala
            'MBD': {'x': 0.68, 'y': 0.32},   # Malakpet
            'GWM': {'x': 0.72, 'y': 0.28},   # Gandhigram
            'PAVP': {'x': 0.75, 'y': 0.25},  # Pavalavagu
            'BZA': {'x': 0.5, 'y': 0.5},     # Vijayawada
        }
        self.map_path = 'Vijayawada_Division_System_map_page-0001 (2).jpg'

    def load_map(self) -> Optional[Image.Image]:
        """Load the base map image"""
        try:
            return Image.open(self.map_path)
        except Exception as e:
            st.error(f"Error loading map: {str(e)}")
            return None

    def highlight_station(self, image: Image.Image, station_code: str) -> Image.Image:
        """Highlight a specific station on the map"""
        if station_code not in self.station_locations:
            return image

        display_image = image.copy()
        width, height = display_image.size
        station_pos = self.station_locations[station_code]
        x = int(station_pos['x'] * width)
        y = int(station_pos['y'] * height)

        # Draw highlight circle
        draw = ImageDraw.Draw(display_image)
        circle_radius = 20
        draw.ellipse(
            [x-circle_radius, y-circle_radius, x+circle_radius, y+circle_radius],
            outline='red',
            width=3
        )

        return display_image

    def render(self, selected_train: Optional[Dict] = None):
        """Render the map with all features"""
        # Load and process map
        base_map = self.load_map()
        if base_map is None:
            return

        # Apply station highlight if train is selected
        display_image = base_map
        if selected_train and 'station' in selected_train:
            display_image = self.highlight_station(display_image, selected_train['station'])
            st.caption(f"Currently showing: {selected_train['station']}")

        # Display the map
        st.image(
            display_image,
            use_container_width=True,
            caption="Vijayawada Division System Map"
        )