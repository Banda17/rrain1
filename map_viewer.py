import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Optional, Tuple

class MapViewer:
    def __init__(self):
        # Station coordinates (normalized to image coordinates 0-1)
        # These coordinates are based on the relative positions on the map
        self.station_locations = {
            'VNEC': {'x': 0.15, 'y': 0.25},   # Secunderabad (left upper)
            'GALA': {'x': 0.25, 'y': 0.30},   # Ghatkesar (middle upper)
            'MBD': {'x': 0.35, 'y': 0.35},    #Malakpet (middle)
            'GWM': {'x': 0.45, 'y': 0.40},    # Gandhinagar (middle lower)
            'PAVP': {'x': 0.55, 'y': 0.45},   # Pavalavagu (right lower)
            'BZA': {'x': 0.75, 'y': 0.60},    # Vijayawada (bottom right)
        }
        self.map_path = 'Vijayawada_Division_System_map_page-0001 (2).jpg'
        self.marker_size = 20  # Size of the train marker

    def load_map(self) -> Optional[Image.Image]:
        """Load the base map image"""
        try:
            return Image.open(self.map_path)
        except Exception as e:
            st.error(f"Error loading map: {str(e)}")
            return None

    def draw_train_marker(self, image: Image.Image, station_code: str, is_selected: bool = False) -> Image.Image:
        """Draw a train marker at the specified station using x,y coordinates"""
        if station_code not in self.station_locations:
            return image

        display_image = image.copy()
        width, height = display_image.size
        station_pos = self.station_locations[station_code]

        # Convert normalized coordinates to pixel positions
        x = int(station_pos['x'] * width)
        y = int(station_pos['y'] * height)

        draw = ImageDraw.Draw(display_image)

        # Marker properties
        marker_color = 'red' if is_selected else 'blue'
        marker_radius = self.marker_size // 2

        # Draw station marker (circle)
        draw.ellipse(
            [(x - marker_radius, y - marker_radius), 
             (x + marker_radius, y + marker_radius)],
            fill=marker_color,
            outline='white',
            width=2
        )

        # Draw station code label
        label_offset = marker_radius + 5
        draw.text(
            (x + label_offset, y - label_offset),
            station_code,
            fill='black',
            stroke_width=1,
            stroke_fill='white'
        )

        # Draw coordinates for debugging
        debug_text = f"({station_pos['x']:.2f}, {station_pos['y']:.2f})"
        draw.text(
            (x + label_offset, y + 5),
            debug_text,
            fill='black',
            stroke_width=1,
            stroke_fill='white'
        )

        return display_image

    def render(self, selected_train: Optional[Dict] = None):
        """Render the map with all features"""
        # Load and process map
        base_map = self.load_map()
        if base_map is None:
            return

        # Create display image
        display_image = base_map.copy()

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

        # Show selected train info
        if selected_train:
            station = selected_train.get('station', '')
            if station in self.station_locations:
                coords = self.station_locations[station]
                st.caption(f"Selected Train at {station} (x: {coords['x']:.2f}, y: {coords['y']:.2f})")