"""
geocoder.py - Location Geocoding

Converts place names to geographic coordinates using geopy/Nominatim.
Handles rate limiting and graceful failure for unreachable locations.
"""

import time
from typing import Dict, List, Optional, Any

try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False


# Rate limiting: Nominatim requires at least 1 second between requests
GEOCODE_DELAY = 1.1  # seconds


class Geocoder:
    """
    Geocoder class for converting place names to coordinates.
    Uses Nominatim (OpenStreetMap) as the geocoding service.
    """
    
    def __init__(self, user_agent: str = "disaster_geo_module"):
        """
        Initialize the geocoder.
        
        Args:
            user_agent: Identifier for API requests (required by Nominatim)
        """
        self.user_agent = user_agent
        self.last_request_time = 0
        
        if GEOPY_AVAILABLE:
            self.geolocator = Nominatim(user_agent=user_agent, timeout=10)
        else:
            self.geolocator = None
    
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < GEOCODE_DELAY:
            time.sleep(GEOCODE_DELAY - elapsed)
        self.last_request_time = time.time()
    
    def geocode_single(self, place_name: str, region_hint: str = "India") -> Optional[Dict[str, Any]]:
        """
        Geocode a single place name.
        
        Args:
            place_name: The location name to geocode
            region_hint: Region to bias results toward
            
        Returns:
            Dict with lat, lon, display_name, or None if not found
        """
        if not GEOPY_AVAILABLE or self.geolocator is None:
            return None
        
        if not place_name or not place_name.strip():
            return None
        
        # Add region hint for better results
        query = f"{place_name}, {region_hint}"
        
        self._rate_limit()
        
        try:
            location = self.geolocator.geocode(query)
            
            if location:
                return {
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "display_name": location.address,
                    "raw_query": place_name
                }
            else:
                return None
                
        except GeocoderTimedOut:
            print(f"[Geocoder] Timeout for: {place_name}")
            return None
        except GeocoderServiceError as e:
            print(f"[Geocoder] Service error for {place_name}: {e}")
            return None
        except Exception as e:
            print(f"[Geocoder] Unexpected error for {place_name}: {e}")
            return None
    
    def geocode_multiple(self, place_names: List[str], region_hint: str = "India") -> List[Dict[str, Any]]:
        """
        Geocode multiple place names and return all successful results.
        
        Args:
            place_names: List of location names to geocode
            region_hint: Region to bias results toward
            
        Returns:
            List of geocoding results (only successful ones)
        """
        results = []
        
        for name in place_names:
            result = self.geocode_single(name, region_hint)
            if result:
                results.append(result)
        
        return results
    
    def geocode_best(self, place_names: List[str], region_hint: str = "India") -> Optional[Dict[str, Any]]:
        """
        Geocode multiple place names and return the best (first successful) result.
        
        The logic prioritizes the first location name since extraction already
        orders them by relevance (OCR text often most reliable).
        
        Args:
            place_names: List of location names to geocode
            region_hint: Region to bias results toward
            
        Returns:
            Best geocoding result, or None if all fail
        """
        for name in place_names:
            result = self.geocode_single(name, region_hint)
            if result:
                return result
        
        return None


# Module-level geocoder instance
_geocoder: Optional[Geocoder] = None


def get_geocoder() -> Geocoder:
    """Get or create the module-level geocoder instance."""
    global _geocoder
    if _geocoder is None:
        _geocoder = Geocoder()
    return _geocoder


def geocode(place_name: str, region_hint: str = "India") -> Optional[Dict[str, Any]]:
    """
    Convenience function to geocode a single place name.
    
    Args:
        place_name: The location name to geocode
        region_hint: Region to bias results toward
        
    Returns:
        Dict with lat, lon, display_name, or None if not found
    """
    return get_geocoder().geocode_single(place_name, region_hint)


def geocode_best(place_names: List[str], region_hint: str = "India") -> Optional[Dict[str, Any]]:
    """
    Convenience function to geocode multiple names and get best result.
    
    Args:
        place_names: List of location names to geocode
        region_hint: Region to bias results toward
        
    Returns:
        Best geocoding result, or None if all fail
    """
    return get_geocoder().geocode_best(place_names, region_hint)


if __name__ == "__main__":
    # Test geocoding
    print("=== Geocoding Test ===\n")
    print(f"geopy available: {GEOPY_AVAILABLE}\n")
    
    test_places = [
        "Silk Board Junction Bangalore",
        "KR Puram Underpass",
        "Marathahalli Bangalore",
        "NonexistentPlace12345"
    ]
    
    for place in test_places:
        result = geocode(place)
        print(f"Query: {place}")
        if result:
            print(f"  Lat: {result['latitude']}")
            print(f"  Lon: {result['longitude']}")
            print(f"  Name: {result['display_name'][:60]}...")
        else:
            print("  NOT FOUND")
        print("-" * 50)
