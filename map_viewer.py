import streamlit as st
from PIL import Image, ImageDraw, ImageFont
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
        self.marker_size = 30  # Size of the train marker

    def load_map(self) -> Optional[Image.Image]:
        """Load the base map image"""
        try:
            return Image.open(self.map_path)
        except Exception as e:
            st.error(f"Error loading map: {str(e)}")
            return None

    def draw_train_marker(self, image: Image.Image, station_code: str, is_selected: bool = False) -> Image.Image:
        """Draw a train marker at the specified station"""
        if station_code not in self.station_locations:
            return image

        display_image = image.copy()
        width, height = display_image.size
        station_pos = self.station_locations[station_code]
        x = int(station_pos['x'] * width)
        y = int(station_pos['y'] * height)

        draw = ImageDraw.Draw(display_image)

        # Draw train marker
        marker_color = 'red' if is_selected else 'blue'
        marker_radius = self.marker_size // 2

        # Draw train icon (simplified train shape)
        points = [
            (x - marker_radius, y + marker_radius),  # bottom left
            (x + marker_radius, y + marker_radius),  # bottom right
            (x + marker_radius, y - marker_radius),  # top right
            (x - marker_radius, y - marker_radius),  # top left
        ]

        # Draw train body
        draw.polygon(points, fill=marker_color, outline='white')

        # Draw windows
        window_size = marker_radius // 2
        draw.rectangle([x - window_size, y - window_size, x + window_size, y], 
                      fill='white', outline=marker_color)

        # Add station name
        draw.text((x + marker_radius + 5, y - marker_radius), 
                 station_code, fill='black', stroke_width=2)

        return display_image

    def render(self, selected_train: Optional[Dict] = None):
        """Render the map with all features"""
        # Load and process map
        base_map = self.load_map()
        if base_map is None:
            return

        # Apply train markers
        display_image = base_map

        # Draw markers for all stations
        for station in self.station_locations.keys():
            is_selected = (selected_train and selected_train.get('station') == station)
            display_image = self.draw_train_marker(display_image, station, is_selected)

        # Display the map
        st.image(
            display_image,
            use_container_width=True,
            caption="Vijayawada Division System Map"
        )

        if selected_train:
            st.caption(f"Currently showing: Train at {selected_train['station']}")