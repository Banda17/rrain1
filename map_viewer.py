import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Optional

class MapViewer:

    def __init__(self):
        # Station coordinates (normalized to image coordinates 0-1)
        self.station_locations = {
            # Main junction stations
            'BZA': {'x': 0.65, 'y': 0.60},  # Vijayawada
            'GDR': {'x': 0.22, 'y': 0.15},  # Gudur
            'TADI': {'x': 0.10, 'y': 0.55},  # Thadi

            # Vijayawada to Gudur route (decreasing y coordinates)
            'MTM': {'x': 0.60, 'y': 0.55},   # Mangalagiri
            'NDL': {'x': 0.55, 'y': 0.50},   # Nidadavolu
            'RJY': {'x': 0.50, 'y': 0.45},   # Rajahmundry
            'ANV': {'x': 0.45, 'y': 0.40},   # Anakapalle
            'VSKP': {'x': 0.40, 'y': 0.35},  # Visakhapatnam
            'VZM': {'x': 0.35, 'y': 0.30},   # Vizianagaram
            'SKM': {'x': 0.30, 'y': 0.25},   # Srikakulam
            'PLH': {'x': 0.25, 'y': 0.20},   # Palasa

            # Thadi to Vijayawada route (increasing x coordinates)
            'KDGL': {'x': 0.15, 'y': 0.56},  # Kondagal
            'MRGA': {'x': 0.20, 'y': 0.57},  # Miryalaguda
            'NLDA': {'x': 0.25, 'y': 0.58},  # Nalgonda
            'PGDP': {'x': 0.30, 'y': 0.59},  # Pagidipalli
            'NDKD': {'x': 0.35, 'y': 0.59},  # Nadikudi
            'GNTW': {'x': 0.40, 'y': 0.60},  # Guntur West
            'GUNT': {'x': 0.45, 'y': 0.60},  # Guntur
            'MNGT': {'x': 0.50, 'y': 0.60},  # Mangalagiri

            # Additional important stations
            'TEL': {'x': 0.32, 'y': 0.22},   # Tuni
            'OGL': {'x': 0.42, 'y': 0.32},   # Ongole
            'NLPR': {'x': 0.27, 'y': 0.18},  # Nellore
        }
        self.map_path = 'Vijayawada_Division_System_map_page-0001 (2).png'
        self.gps_pin_path = 'gps_pin.png'
        self.base_marker_size = 20  # Reduced marker size for better visibility
        self.max_image_size = (1024, 768)  # Adjusted for the map's aspect ratio
        self.zoom_level = 1.0  # Default zoom level

    def get_station_coordinates(
            self, station_code: str) -> Optional[Dict[str, float]]:
        """Get coordinates for a station code"""
        return self.station_locations.get(station_code)

    def load_map(self) -> Optional[Image.Image]:
        """Load the map image"""
        try:
            # Set a reasonable limit for large images
            Image.MAX_IMAGE_PIXELS = 178956970  # Safe limit for large images

            # Load and convert the image
            image = Image.open(self.map_path).convert('RGBA')

            # Resize if needed while maintaining aspect ratio
            width, height = image.size
            if width > self.max_image_size[0] or height > self.max_image_size[1]:
                scale = min(
                    self.max_image_size[0] / width,
                    self.max_image_size[1] / height
                )
                new_size = (int(width * scale), int(height * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            return image
        except Exception as e:
            st.error(f"Error loading map: {str(e)}")
            return None

    def load_gps_pin(self, size: int) -> Optional[Image.Image]:
        """Load and resize the GPS pin image"""
        try:
            gps_pin = Image.open(self.gps_pin_path).convert('RGBA')
            resized_pin = gps_pin.resize((size, size),
                                       Image.Resampling.LANCZOS)
            return resized_pin
        except Exception as e:
            st.error(f"Error loading GPS pin: {str(e)}")
            return None

    def draw_train_marker(self, image: Image.Image,
                         station_code: str) -> Image.Image:
        """Draw a GPS pin marker at the specified station"""
        station_pos = self.get_station_coordinates(station_code)
        if not station_pos:
            return image

        display_image = image.convert('RGBA')
        width, height = display_image.size
        x = int(station_pos['x'] * width)
        y = int(station_pos['y'] * height)

        marker_size = int(self.base_marker_size * self.zoom_level)
        gps_pin = self.load_gps_pin(marker_size)

        if gps_pin:
            paste_x = x - marker_size // 2
            paste_y = y - marker_size // 2

            temp = Image.new('RGBA', display_image.size, (0, 0, 0, 0))
            temp.paste(gps_pin, (paste_x, paste_y), gps_pin)

            display_image = Image.alpha_composite(display_image, temp)

        display_image = display_image.convert('RGB')
        draw = ImageDraw.Draw(display_image)

        font_size = int(12 * self.zoom_level)  # Adjusted font size
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except:
            font = None

        label_offset = marker_size // 2 + 5
        draw.text((x + label_offset, y - label_offset),
                 station_code,
                 fill='black',
                 stroke_width=2,
                 stroke_fill='white',
                 font=font)

        return display_image

    def render(self, selected_train: Optional[Dict] = None):
        """Render the map with all features"""
        st.write("## Interactive Map View")

        show_coords = st.checkbox(
            "Show Coordinates",
            value=False,
            help="Display station coordinates on the map")

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
                station_code = selected_train['station']
                if station_code in self.station_locations:
                    display_image = self.draw_train_marker(
                        display_image, station_code)

            display_image = display_image.convert('RGB')
            original_width, original_height = display_image.size

            max_height = 400
            height_ratio = max_height / original_height
            new_width = int(original_width * height_ratio * 1.2)
            new_height = max_height

            display_image = display_image.resize((new_width, new_height),
                                                 Image.Resampling.LANCZOS)

            st.image(display_image,
                     use_container_width=True,
                     caption="Vijayawada Division System Map")

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