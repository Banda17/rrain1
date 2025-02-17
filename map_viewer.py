import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Optional, Tuple
import io

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
        self.max_image_size = (2048, 2048)  # Maximum dimensions for the base map

    def load_map(self) -> Optional[Image.Image]:
        """Load and safely resize the base map image"""
        try:
            # Open image with Pillow's maximum size limit set
            Image.MAX_IMAGE_PIXELS = 178956970  # Safe limit
            original_image = Image.open(self.map_path)

            # Calculate new dimensions while maintaining aspect ratio
            width, height = original_image.size
            scale = min(
                self.max_image_size[0] / width,
                self.max_image_size[1] / height
            )

            if scale < 1:  # Only resize if image is too large
                new_width = int(width * scale)
                new_height = int(height * scale)
                resized_image = original_image.resize(
                    (new_width, new_height),
                    Image.Resampling.LANCZOS
                )
                return resized_image
            return original_image

        except Exception as e:
            st.error(f"Error loading map: {str(e)}")
            return None

    def draw_train_marker(self, image: Image.Image, station_code: str, is_selected: bool = False, zoom_level: float = 1.0) -> Image.Image:
        """Draw a train marker at the specified station using x,y coordinates"""
        if station_code not in self.station_locations or not is_selected:
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

        # Draw station marker (circle with pulsing effect)
        # Inner circle
        draw.ellipse(
            [(x - marker_radius, y - marker_radius), 
             (x + marker_radius, y + marker_radius)],
            fill='red',
            outline='white',
            width=max(2, int(zoom_level))
        )

        # Outer circle for highlight effect
        outer_radius = int(marker_radius * 1.5)
        draw.ellipse(
            [(x - outer_radius, y - outer_radius),
             (x + outer_radius, y + outer_radius)],
            fill=None,
            outline='yellow',
            width=max(2, int(zoom_level))
        )

        # Scale text size with zoom
        font_size = int(14 * zoom_level)  # Increased base font size
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except:
            font = None  # Will use default font if custom font not available

        # Draw station code label with improved visibility
        label_offset = marker_radius + 5
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

        # Create columns for controls
        col1, col2 = st.columns([2, 1])

        with col1:
            # Add zoom control
            zoom_level = st.slider("Zoom Level", min_value=1.0, max_value=4.0, value=1.5, step=0.1,
                                help="Drag to zoom in/out of the map")

        with col2:
            # Add display options
            show_coords = st.checkbox("Show Coordinates", value=False,
                                    help="Display station coordinates on the map")

        # Load and process map
        base_map = self.load_map()
        if base_map is None:
            return

        # Create display container
        map_container = st.container()
        with map_container:
            # Create display image
            display_image = base_map.copy()

            # Draw markers only for selected train's station
            if selected_train and selected_train.get('station') in self.station_locations:
                display_image = self.draw_train_marker(display_image, selected_train['station'], True, zoom_level)

            # Calculate new dimensions based on zoom
            original_width, original_height = display_image.size
            new_width = int(original_width * zoom_level)
            new_height = int(original_height * zoom_level)

            # Resize image
            display_image = display_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Display the map with increased size
            st.image(
                display_image,
                use_container_width=True,  # Updated from use_column_width
                caption="Vijayawada Division System Map (Use slider to zoom)"
            )

            # Show hover information for selected train
            if selected_train:
                station = selected_train.get('station', '')
                if station in self.station_locations:
                    with st.expander("🚂 Train Information", expanded=True):
                        st.markdown(f"""
                        **Train Details:**
                        - Train Number: {selected_train.get('train', '')}
                        - Station: {station}
                        - Position: {'(' + f"{self.station_locations[station]['x']:.2f}, {self.station_locations[station]['y']:.2f}" + ')' if show_coords else ''}

                        Hover over the marker on the map to see the location!
                        """)