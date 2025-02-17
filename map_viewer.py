import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Optional, Tuple
import io

class MapViewer:
    def __init__(self):
        # Station coordinates (normalized to image coordinates 0-1)
        self.station_locations = {
            'VNEC': {'x': 0.15, 'y': 0.25},   # Secunderabad (left upper)
            'GALA': {'x': 0.25, 'y': 0.30},   # Ghatkesar (middle upper)
            'MBD': {'x': 0.35, 'y': 0.35},    # Malakpet (middle)
            'GWM': {'x': 0.45, 'y': 0.40},    # Gandhinagar (middle lower)
            'PAVP': {'x': 0.55, 'y': 0.45},   # Pavalavagu (right lower)
            'BZA': {'x': 0.75, 'y': 0.60},    # Vijayawada (bottom right)
        }
        self.map_path = 'Vijayawada_Division_System_map_page-0001 (2).jpg'
        self.gps_pin_path = 'gps_pin.png'  # Path to your GPS pin image
        self.base_marker_size = 100  # Larger size for the GPS pin
        self.max_image_size = (2048, 2048)  # Maximum dimensions for the base map
        self.default_zoom = 1.5
        self.max_zoom = 4.0

    def get_station_coordinates(self, station_code: str) -> Optional[Dict[str, float]]:
        """Get coordinates for a station code"""
        return self.station_locations.get(station_code)

    def load_map(self) -> Optional[Image.Image]:
        """Load and safely resize the base map image"""
        try:
            Image.MAX_IMAGE_PIXELS = 178956970  # Safe limit
            original_image = Image.open(self.map_path).convert('RGBA')

            width, height = original_image.size
            scale = min(self.max_image_size[0] / width, self.max_image_size[1] / height)

            if scale < 1:  # Only resize if image is too large
                new_width = int(width * scale)
                new_height = int(height * scale)
                resized_image = original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                return resized_image
            return original_image

        except Exception as e:
            st.error(f"Error loading map: {str(e)}")
            return None

    def load_gps_pin(self, size: int) -> Optional[Image.Image]:
        """Load and resize the GPS pin image"""
        try:
            # Open image and ensure it's in RGBA mode
            gps_pin = Image.open(self.gps_pin_path).convert('RGBA')
            resized_pin = gps_pin.resize((size, size), Image.Resampling.LANCZOS)
            return resized_pin

        except Exception as e:
            st.error(f"Error loading GPS pin: {str(e)}")
            return None

    def draw_train_marker(self, image: Image.Image, station_code: str, zoom_level: float = 1.0) -> Image.Image:
        """Draw a GPS pin marker at the specified station using x,y coordinates"""
        station_pos = self.get_station_coordinates(station_code)
        if not station_pos:
            return image

        # Ensure display image is in RGBA mode
        display_image = image.convert('RGBA')
        width, height = display_image.size
        x = int(station_pos['x'] * width)
        y = int(station_pos['y'] * height)

        marker_size = int(self.base_marker_size * zoom_level)
        gps_pin = self.load_gps_pin(marker_size)

        if gps_pin:
            # Calculate paste position to center the pin
            paste_x = x - marker_size // 2
            paste_y = y - marker_size // 2

            # Create a new blank image with alpha channel
            temp = Image.new('RGBA', display_image.size, (0, 0, 0, 0))
            temp.paste(gps_pin, (paste_x, paste_y), gps_pin)

            # Composite the images
            display_image = Image.alpha_composite(display_image, temp)

        # Convert back to RGB for drawing text
        display_image = display_image.convert('RGB')
        draw = ImageDraw.Draw(display_image)

        font_size = int(14 * zoom_level)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except:
            font = None

        label_offset = marker_size // 2 + 5
        draw.text(
            (x + label_offset, y - label_offset),
            station_code,
            fill='black',
            stroke_width=max(2, int(zoom_level)),
            stroke_fill='white',
            font=font
        )

        return display_image

    def render(self, selected_train: Optional[Dict] = None):
        """Render the map with all features"""
        st.write("## Interactive Map Controls")

        zoom_level = st.slider(
            "Zoom Level",
            min_value=1.0,
            max_value=self.max_zoom,
            value=self.default_zoom,
            step=0.1,
            help="Drag to zoom in/out of the map"
        )

        show_coords = st.checkbox(
            "Show Coordinates",
            value=False,
            help="Display station coordinates on the map"
        )

        # Cache the base map loading
        @st.cache_data(ttl=3600)
        def get_base_map():
            return self.load_map()

        base_map = get_base_map()
        if base_map is None:
            return

        map_container = st.container()
        with map_container:
            display_image = base_map.copy()

            if selected_train and selected_train.get('station'):
                # Directly check if station exists in coordinates
                station_code = selected_train['station']
                if station_code in self.station_locations:
                    display_image = self.draw_train_marker(
                        display_image,
                        station_code,
                        zoom_level
                    )

            # Convert to RGB before resizing and display
            display_image = display_image.convert('RGB')
            original_width, original_height = display_image.size
            new_width = int(original_width * zoom_level)
            new_height = int(original_height * zoom_level)
            display_image = display_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            st.image(
                display_image,
                use_container_width=True,
                caption="Vijayawada Division System Map (Use slider to zoom)"
            )

            if selected_train and selected_train.get('station'):
                station = selected_train['station']
                if station in self.station_locations:
                    with st.expander("🚂 Train Information", expanded=True):
                        st.markdown(f"""
                        **Train Details:**
                        - Train Number: {selected_train.get('train', '')}
                        - Station: {station}
                        - Position: {'(' + f"{self.station_locations[station]['x']:.2f}, {self.station_locations[station]['y']:.2f}" + ')' if show_coords else ''}
                        """)