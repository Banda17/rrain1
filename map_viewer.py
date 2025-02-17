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
        self.base_marker_size = 20  # Base size of the train marker

    def load_map(self) -> Optional[Image.Image]:
        """Load the base map image"""
        try:
            return Image.open(self.map_path)
        except Exception as e:
            st.error(f"Error loading map: {str(e)}")
            return None

    def draw_train_marker(self, image: Image.Image, station_code: str, is_selected: bool = False, zoom_level: float = 1.0) -> Image.Image:
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

        # Scale marker size with zoom level
        marker_size = int(self.base_marker_size * zoom_level)
        marker_radius = marker_size // 2

        # Marker properties
        marker_color = 'red' if is_selected else 'blue'

        # Draw station marker (circle)
        draw.ellipse(
            [(x - marker_radius, y - marker_radius), 
             (x + marker_radius, y + marker_radius)],
            fill=marker_color,
            outline='white',
            width=max(2, int(zoom_level))
        )

        # Scale text size with zoom
        font_size = int(12 * zoom_level)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except:
            font = None  # Will use default font if custom font not available

        # Draw station code label
        label_offset = marker_radius + 5
        draw.text(
            (x + label_offset, y - label_offset),
            station_code,
            fill='black',
            stroke_width=max(1, int(zoom_level/2)),
            stroke_fill='white',
            font=font
        )

        # Draw coordinates for debugging
        debug_text = f"({station_pos['x']:.2f}, {station_pos['y']:.2f})"
        draw.text(
            (x + label_offset, y + 5),
            debug_text,
            fill='black',
            stroke_width=max(1, int(zoom_level/2)),
            stroke_fill='white',
            font=font
        )

        return display_image

    def render(self, selected_train: Optional[Dict] = None):
        """Render the map with all features"""
        st.write("## Interactive Map Controls")

        # Add zoom control
        zoom_level = st.slider("Zoom Level", min_value=1.0, max_value=3.0, value=1.5, step=0.1)

        # Load and process map
        base_map = self.load_map()
        if base_map is None:
            return

        # Create display container with expanded width
        map_container = st.container()
        with map_container:
            # Create display image
            display_image = base_map.copy()

            # Draw markers for all stations
            for station in self.station_locations.keys():
                is_selected = (selected_train and selected_train.get('station') == station)
                display_image = self.draw_train_marker(display_image, station, is_selected, zoom_level)

            # Calculate new dimensions based on zoom
            original_width, original_height = display_image.size
            new_width = int(original_width * zoom_level)
            new_height = int(original_height * zoom_level)

            # Resize image
            display_image = display_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Display the map with increased size
            st.image(
                display_image,
                use_column_width=True,
                caption="Vijayawada Division System Map (Use slider to zoom)"
            )

            # Show selected train info
            if selected_train:
                station = selected_train.get('station', '')
                if station in self.station_locations:
                    coords = self.station_locations[station]
                    st.caption(f"Selected Train at {station} (x: {coords['x']:.2f}, y: {coords['y']:.2f})")