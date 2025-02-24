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
        Get the map bounds for Andhra Pradesh region.
        Returns (min_lat, max_lat, min_lon, max_lon)
        """
        return (13.5, 19.5, 77.5, 84.5)  # Andhra Pradesh region bounds

    def create_offline_map(self, center: Tuple[float, float], zoom: int = 8) -> Optional[folium.Map]:
        """
        Create a folium map with offline tile layer
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

            # Add custom tile layer
            bounds = self.get_map_bounds()
            folium.raster_layers.ImageOverlay(
                image=self.map_path,
                bounds=[[bounds[0], bounds[2]], [bounds[1], bounds[3]]],
                opacity=0.8,
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