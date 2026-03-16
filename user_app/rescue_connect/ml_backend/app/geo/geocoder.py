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
        """
        if not GEOPY_AVAILABLE or self.geolocator is None:
            return None
        
        if not place_name or not place_name.strip():
            return None
            
        # Spelling Normalization for common Indian/Chennai names
        # This helps map colloquial names to official OSM names
        SPELLING_CORRECTIONS = {
            "theagaraya": "Sir Thyagaraya",
            "thyagaraya": "Sir Thyagaraya",
            "thiyagaraya": "Sir Thyagaraya",
            "pondy bazaar": "Pondy Bazaar", # Ensure distinct
            "mount road": "Anna Salai"      # Common Chennai alias
        }
        
        query_norm = place_name
        query_lower = place_name.lower()
        
        for k, v in SPELLING_CORRECTIONS.items():
            if k in query_lower:
                # Replace the keyword case-insensitively
                import re
                query_norm = re.sub(re.escape(k), v, query_norm, flags=re.IGNORECASE)
                break # Prevent re-matching (e.g. "Sir Thyagaraya" replacing itself)
        
        # Add region hint for better results
        query = f"{query_norm}, {region_hint}"
        
        try:
            self._rate_limit()
            # Enforce India-only results using country_codes
            # Get multiple results to allow filtering/prioritization
            results = self.geolocator.geocode(query, country_codes="in", exactly_one=False, limit=5)
            
            if results:
                return self._process_results(results, place_name)
                
            # Fallback 1: Try original query if normalization failed
            if query_norm != place_name:
                query = f"{place_name}, {region_hint}"
                self._rate_limit()
                results = self.geolocator.geocode(query, country_codes="in", exactly_one=False, limit=5)
                if results:
                    return self._process_results(results, place_name)
                    
            # Fallback 2: Recursive stripping of last word (e.g. "Sir Thyagaraya Road" -> "Sir Thyagaraya")
            words = query_norm.split()
            if len(words) > 1:
                short_query = " ".join(words[:-1]) # Remove last word ("Road")
                query = f"{short_query}, {region_hint}"
                self._rate_limit()
                results = self.geolocator.geocode(query, country_codes="in", exactly_one=False, limit=5)
                if results:
                    return self._process_results(results, place_name)

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
    
    def _process_results(self, results, place_name):
        """Helper to process and prioritize geocoding results."""
        best_match = results[0]
        query_lower = place_name.lower()
        road_keywords = ["road", "street", "st", "rd", "lane", "sarani", "salai", "marg", "dr", "way", "highway", "flyover", "bridge"]
        
        if any(w in query_lower for w in road_keywords):
            for res in results:
                cls = res.raw.get("class", "")
                if cls == "highway":
                    best_match = res
                    break
                    
        location = best_match
        granularity = location.raw.get("addresstype") or location.raw.get("type", "unknown")
        
        # Re-check mismatch on the final selected result
        is_road_query = any(w in query_lower for w in road_keywords)
        best_cls = location.raw.get("class", "")
        road_mismatch = False
        if is_road_query and best_cls != "highway":
            if best_cls not in ["place", "boundary"]:
                road_mismatch = True

        return {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "display_name": location.address,
            "raw_query": place_name,
            "granularity": granularity,
            "road_mismatch": road_mismatch
        }

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
