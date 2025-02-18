import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Optional


class MapViewer:

    def __init__(self):
        # Station coordinates (normalized to image coordinates 0-1)
        self.station_locations = {
            'VNEC': {
                'x': 0.15,
                'y': 0.25
            },
            'GALA': {
                'x': 0.25,
                'y': 0.30
            },
            'MBD': {
                'x': 0.35,
                'y': 0.35
            },
            'GWM': {
                'x': 0.45,
                'y': 0.40
            },
            'PAVP': {
                'x': 0.55,
                'y': 0.45
            },
            'BZA': {
                'x': -1.00,
                'y': -1.00
            },
            'KJJ': {
                'x': 0.78,
                'y': 0.62
            },
            'PGU': {
                'x': 0.80,
                'y': 0.64
            },
            'NLR': {
                'x': 0.82,
                'y': 0.66
            },
            'VDE': {
                'x': 0.84,
                'y': 0.68
            },
            'VKT': {
                'x': 0.86,
                'y': 0.70
            },
            'KMLP': {
                'x': 0.88,
                'y': 0.72
            },
            'PVD': {
                'x': 0.90,
                'y': 0.74
            },
            'KCC': {
                'x': 0.50,
                'y': 0.50
            },
            'TMC': {
                'x': 0.76,
                'y': 0.60
            },
            'AXR': {
                'x': 0.74,
                'y': 0.58
            },
            'BTTR': {
                'x': 0.72,
                'y': 0.62
            },
            'SVPM': {
                'x': 0.70,
                'y': 0.60
            },
            'KVZ': {
                'x': 0.68,
                'y': 0.58
            },
            'TTU': {
                'x': 0.66,
                'y': 0.56
            },
            'UPD': {
                'x': 0.64,
                'y': 0.54
            },
            'SKM': {
                'x': 0.62,
                'y': 0.52
            },
            'TNR': {
                'x': 0.60,
                'y': 0.50
            },
            'SDM': {
                'x': 0.58,
                'y': 0.48
            },
            'OGL': {
                'x': 0.56,
                'y': 0.46
            },
            'KRV': {
                'x': 0.54,
                'y': 0.44
            },
            'ANB': {
                'x': 0.52,
                'y': 0.42
            },
            'UGD': {
                'x': 0.50,
                'y': 0.40
            },
            'CJM': {
                'x': 0.48,
                'y': 0.38
            },
            'VTM': {
                'x': 0.46,
                'y': 0.36
            },
            'CLX': {
                'x': 0.44,
                'y': 0.34
            },
            'SPF': {
                'x': 0.42,
                'y': 0.32
            },
            'BPP': {
                'x': 0.40,
                'y': 0.30
            },
            'APL': {
                'x': 0.38,
                'y': 0.28
            },
            'NDO': {
                'x': 0.36,
                'y': 0.26
            },
            'TSR': {
                'x': 0.34,
                'y': 0.24
            },
            'TEL': {
                'x': 0.32,
                'y': 0.22
            },
            'DIG': {
                'x': 0.28,
                'y': 0.18
            },
            'MBL': {
                'x': 0.25,
                'y': 0.92
            },
            'GDR': {
                'x': 0.25,
                'y': 0.93
            }
        }
        self.map_path = 'Vijayawada_Division_System_map_page-0001 (2).png'
        self.gps_pin_path = 'gps_pin.png'
        self.base_marker_size = 50
        self.max_image_size = (2048, 2048)
        self.zoom_level = 1.5

    def get_station_coordinates(
            self, station_code: str) -> Optional[Dict[str, float]]:
        """Get coordinates for a station code"""
        return self.station_locations.get(station_code)

    def load_map(self) -> Optional[Image.Image]:
        """Load and safely resize the base map image"""
        try:
            Image.MAX_IMAGE_PIXELS = 178956970  # Safe limit
            original_image = Image.open(self.map_path).convert('RGBA')

            width, height = original_image.size
            scale = min(self.max_image_size[0] / width,
                       self.max_image_size[1] / height)

            if scale < 1:  # Only resize if image is too large
                new_width = int(width * scale)
                new_height = int(height * scale)
                resized_image = original_image.resize((new_width, new_height),
                                                    Image.Resampling.LANCZOS)
                return resized_image
            return original_image

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

        font_size = int(14 * self.zoom_level)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except:
            font = None

        label_offset = marker_size // 2 + 5
        draw.text((x + label_offset, y - label_offset),
                 station_code,
                 fill='black',
                 stroke_width=max(2, int(self.zoom_level)),
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