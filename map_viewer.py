import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Optional, Tuple
import io

class MapViewer:
    def __init__(self):
        # Station coordinates (normalized to image coordinates 0-1)
        self.station_locations = {
            # Existing reference stations
            'VNEC': {'x': 0.15, 'y': 0.25},   # Secunderabad
            'GALA': {'x': 0.25, 'y': 0.30},   # Ghatkesar
            'MBD': {'x': 0.35, 'y': 0.35},    # Malakpet
            'GWM': {'x': 0.45, 'y': 0.40},    # Gandhinagar
            'PAVP': {'x': 0.55, 'y': 0.45},   # Pavalavagu
            'BZA': {'x': 0.75, 'y': 0.60},    # Vijayawada

            # Vijayawada to Gudur route (increasing x, y coordinates)
            'BVRM': {'x': 0.78, 'y': 0.62},   # Bhimavaram
            'TNKU': {'x': 0.80, 'y': 0.64},   # Tanuku
            'RAJM': {'x': 0.82, 'y': 0.66},   # Rajahmundry
            'VSKP': {'x': 0.84, 'y': 0.68},   # Visakhapatnam
            'VZIP': {'x': 0.86, 'y': 0.70},   # Vizianagaram
            'SCMN': {'x': 0.88, 'y': 0.72},   # Srikakulam
            'PTPU': {'x': 0.90, 'y': 0.74},   # Palasa
            'GDR': {'x': 0.92, 'y': 0.76},    # Gudur

            # Thadi to Vijayawada route (decreasing x coordinates)
            'TADI': {'x': 0.10, 'y': 0.55},   # Thadi
            'KDGL': {'x': 0.15, 'y': 0.56},   # Kondagal
            'MRGA': {'x': 0.20, 'y': 0.57},   # Miryalaguda
            'NLDA': {'x': 0.25, 'y': 0.58},   # Nalgonda
            'PGDP': {'x': 0.30, 'y': 0.59},   # Pagidipalli
            'NDKD': {'x': 0.35, 'y': 0.59},   # Nadikudi
            'GNTW': {'x': 0.40, 'y': 0.60},   # Guntur West
            'GUNT': {'x': 0.45, 'y': 0.60},   # Guntur
            'MNGT': {'x': 0.50, 'y': 0.60},   # Mangalagiri

            # Adding more stations with appropriate spacing
            'BPRD': {'x': 0.83, 'y': 0.67},   # Bhupalapatnam Road
            'ANKL': {'x': 0.85, 'y': 0.69},   # Ankapalle
            'RGDA': {'x': 0.87, 'y': 0.71},   # Rayagada
            'KRPU': {'x': 0.89, 'y': 0.73},   # Koraput
            'KRDL': {'x': 0.91, 'y': 0.75},   # Kirandul

            # Additional stations on branch lines
            'PDPL': {'x': 0.60, 'y': 0.50},   # Piduguralla
            'NDKD': {'x': 0.65, 'y': 0.55},   # Nadikude
            'MCLA': {'x': 0.70, 'y': 0.57},   # Machilipatnam
            'BVRM': {'x': 0.72, 'y': 0.58},   # Bhimavaram

            # Adding more stations for comprehensive coverage
            'TUNI': {'x': 0.83, 'y': 0.67},   # Tuni
            'ANVM': {'x': 0.84, 'y': 0.68},   # Anakapalle
            'VSKP': {'x': 0.85, 'y': 0.69},   # Visakhapatnam
            'SCMN': {'x': 0.86, 'y': 0.70},   # Srikakulam Road
            'CHE': {'x': 0.87, 'y': 0.71},    # Chennai

            # More stations towards Gudur
            'OGL': {'x': 0.88, 'y': 0.72},    # Ongole
            'NLPR': {'x': 0.89, 'y': 0.73},   # Nellore
            'GDR': {'x': 0.90, 'y': 0.74},    # Gudur
        }
        self.map_path = 'Vijayawada_Division_System_map_page-0001 (2).jpg'
        self.gps_pin_path = 'gps_pin.png'
        self.base_marker_size = 100
        self.max_image_size = (2048, 2048)
        self.zoom_level = 1.5

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
            gps_pin = Image.open(self.gps_pin_path).convert('RGBA')
            resized_pin = gps_pin.resize((size, size), Image.Resampling.LANCZOS)
            return resized_pin

        except Exception as e:
            st.error(f"Error loading GPS pin: {str(e)}")
            return None

    def draw_train_marker(self, image: Image.Image, station_code: str) -> Image.Image:
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

        font_size = int(14 * self.zoom_level)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except:
            font = None

        label_offset = marker_size // 2 + 5
        draw.text(
            (x + label_offset, y - label_offset),
            station_code,
            fill='black',
            stroke_width=max(2, int(self.zoom_level)),
            stroke_fill='white',
            font=font
        )

        return display_image

    def render(self, selected_train: Optional[Dict] = None):
        """Render the map with all features"""
        st.write("## Interactive Map View")

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
                station_code = selected_train['station']
                if station_code in self.station_locations:
                    display_image = self.draw_train_marker(
                        display_image,
                        station_code
                    )

            display_image = display_image.convert('RGB')
            original_width, original_height = display_image.size

            max_height = 400
            height_ratio = max_height / original_height
            new_width = int(original_width * height_ratio * 1.2)
            new_height = max_height

            display_image = display_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            st.image(
                display_image,
                use_container_width=True,
                caption="Vijayawada Division System Map"
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