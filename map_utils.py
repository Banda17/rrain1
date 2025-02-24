import os
from PIL import Image
import logging

logger = logging.getLogger(__name__)

def prepare_offline_map(map_path: str) -> bool:
    """
    Prepare the map image for offline use with Folium.
    Returns True if successful, False otherwise.
    """
    try:
        # Check if map file exists
        if not os.path.exists(map_path):
            logger.error(f"Map file not found: {map_path}")
            return False
            
        # Load and verify the image
        with Image.open(map_path) as img:
            # Get image dimensions
            width, height = img.size
            logger.info(f"Map dimensions: {width}x{height}")
            
            # Verify image format
            if img.format not in ['PNG', 'JPEG']:
                logger.warning(f"Converting image from {img.format} to PNG")
                img = img.convert('RGB')
                img.save(map_path.replace(os.path.splitext(map_path)[1], '.png'), 'PNG')
                
        return True
        
    except Exception as e:
        logger.error(f"Error preparing offline map: {str(e)}")
        return False
