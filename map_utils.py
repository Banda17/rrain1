import os
from PIL import Image
import logging
import folium
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class OfflineMapHandler:
    def __init__(self, map_path: str):
        self.map_path = map_path
        self.cache_dir = "map_cache"
        # Define Vijayawada GPS coordinates
        self.vijayawada_coords = (16.5167, 80.6167)

    def prepare_map_image(self) -> bool:
        """
        Prepare and validate the map image for offline use.
        Returns True if successful, False otherwise.
        """
        try:
            if not os.path.exists(self.map_path):
                logger.error(f"Map file not found: {self.map_path}")
                return False

            # Load and verify the image
            with Image.open(self.map_path) as img:
                # Get image dimensions
                width, height = img.size
                logger.info(f"Map dimensions: {width}x{height}")

                # Verify image format
                if img.format not in ['PNG', 'JPEG']:
                    logger.warning(f"Converting image from {img.format} to PNG")
                    img = img.convert('RGB')
                    img.save(self.map_path.replace(os.path.splitext(self.map_path)[1], '.png'), 'PNG')

            return True

        except Exception as e:
            logger.error(f"Error preparing map image: {str(e)}")
            return False

    def get_map_bounds(self) -> Tuple[float, float, float, float]:
        """
        Get calibrated map bounds for Vijayawada Division map.
        Adjusted to make Vijayawada point coincide with actual GPS coordinates.

        Returns (min_lat, max_lat, min_lon, max_lon)
        """
        # These bounds are calibrated to align Vijayawada on the map image with its GPS coordinates
        # South-West corner (bottom-left) and North-East corner (top-right)
        # Adjusted to ensure Vijayawada point on the map aligns with actual GPS coordinates
        return (14.5, 19.0, 78.0, 84.0)  # Calibrated bounds for Vijayawada Division

    def create_offline_map(self, center: Tuple[float, float], zoom: int = 8, custom_bounds: Optional[Tuple[float, float, float, float]] = None) -> Optional[folium.Map]:
        """
        Create a folium map with offline tile layer

        Args:
            center: Center coordinates (lat, lon)
            zoom: Initial zoom level
            custom_bounds: Optional custom bounds (min_lat, max_lat, min_lon, max_lon)
        """
        try:
            # Create base map
            m = folium.Map(
                location=center,
                zoom_start=zoom,
                tiles=None
            )

            # Prepare image if needed
            if not self.prepare_map_image():
                return None

            # Use custom bounds if provided, otherwise use default bounds
            bounds = custom_bounds if custom_bounds else self.get_map_bounds()

            # Add a marker for the reference point (Vijayawada)
            folium.Marker(
                self.vijayawada_coords,
                popup="Vijayawada (Reference Point)",
                tooltip="Vijayawada",
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(m)

            # Add the image overlay with calibrated bounds
            folium.raster_layers.ImageOverlay(
                image=self.map_path,
                bounds=[[bounds[0], bounds[2]], [bounds[1], bounds[3]]],
                opacity=0.9,  # Changed from 0.7 to 0.9 to make the image more opaque
                name="Offline Map"
            ).add_to(m)

            # Add OpenStreetMap layer as fallback
            folium.TileLayer(
                tiles='OpenStreetMap',
                name='Online Map (Fallback)',
                attr='OpenStreetMap contributors'
            ).add_to(m)

            # Add layer control
            folium.LayerControl().add_to(m)

            return m

        except Exception as e:
            logger.error(f"Error creating offline map: {str(e)}")
            return None