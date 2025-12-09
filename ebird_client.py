"""
eBird API client for bird observation data.
Handles species code lookup, observation queries, and probability calculations.
"""
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from config import get_ebird_api_key

# Try to import streamlit for caching (only works in Streamlit context)
try:
    import streamlit as st
    HAS_STREAMLIT = True
except (ImportError, RuntimeError):
    HAS_STREAMLIT = False
    # Create a dummy decorator if streamlit is not available
    def cache_data(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    st = type('obj', (object,), {'cache_data': cache_data})()

EBIRD_API_BASE_URL = "https://api.ebird.org/v2"


# Cache taxonomy data
_taxonomy_cache = None

def _load_taxonomy() -> Optional[List[Dict]]:
    """Load eBird taxonomy (cached)."""
    global _taxonomy_cache
    
    if _taxonomy_cache is not None:
        return _taxonomy_cache
    
    try:
        api_key = get_ebird_api_key()
    except ValueError as e:
        print(f"API key configuration error: {str(e)}")
        return None
    
    # eBird API returns CSV by default, but we'll try both formats
    url = f"{EBIRD_API_BASE_URL}/ref/taxonomy/ebird"
    
    try:
        # Try CSV format first (default for eBird API)
        headers_csv = {
            "X-eBirdApiToken": api_key
        }
        response = requests.get(url, headers=headers_csv, timeout=30)
        response.raise_for_status()
        
        # Check if response is empty
        if not response.text or not response.text.strip():
            print("eBird API returned empty response")
            return None
        
        # Try to parse as CSV first (most common format)
        try:
            import csv
            from io import StringIO
            csv_reader = csv.DictReader(StringIO(response.text))
            taxonomy = list(csv_reader)
            if taxonomy and len(taxonomy) > 0:
                _taxonomy_cache = taxonomy
                return taxonomy
        except Exception as csv_error:
            # If CSV parsing fails, try JSON
            pass
        
        # Try JSON format
        try:
            taxonomy = response.json()
            if isinstance(taxonomy, list) and len(taxonomy) > 0:
                _taxonomy_cache = taxonomy
                return taxonomy
        except ValueError:
            pass
        
        # Log response details for debugging
        content_type = response.headers.get('Content-Type', 'unknown')
        print(f"Could not parse eBird taxonomy response.")
        print(f"Content-Type: {content_type}")
        print(f"Response length: {len(response.text)}")
        print(f"Content preview: {response.text[:500]}")
        return None
        
    except requests.exceptions.Timeout:
        print("eBird API request timed out")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("Invalid eBird API key")
        elif e.response.status_code == 429:
            print("eBird API rate limit exceeded")
        else:
            print(f"eBird API error (HTTP {e.response.status_code}): {str(e)}")
            print(f"Response content: {e.response.text[:200]}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching eBird taxonomy: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error loading taxonomy: {str(e)}")
        return None


def get_species_code(bird_name: str, scientific_name: str = "") -> Optional[str]:
    """
    Convert bird name to eBird species code using eBird taxonomy API.
    
    Args:
        bird_name: Common name of the bird (e.g., "Carolina Wren")
        scientific_name: Optional scientific name (e.g., "Thryothorus ludovicianus")
    
    Returns:
        eBird species code (e.g., "carwre") or None if not found
    """
    if not bird_name or not bird_name.strip():
        return None
    
    taxonomy = _load_taxonomy()
    if not taxonomy:
        return None
    
    # Normalize field names (eBird API uses different formats)
    def get_com_name(species):
        for field in ["comName", "COMMON_NAME", "common_name", "Common Name", "commonName"]:
            if field in species and species[field]:
                return str(species[field])
        return ""
    
    def get_sci_name(species):
        for field in ["sciName", "SCIENTIFIC_NAME", "scientific_name", "Scientific Name", "sciName"]:
            if field in species and species[field]:
                return str(species[field])
        return ""
    
    def get_species_code_field(species):
        for field in ["speciesCode", "SPECIES_CODE", "species_code", "Species Code", "speciesCode"]:
            if field in species and species[field]:
                return str(species[field])
        return ""
    
    bird_name_lower = bird_name.lower().strip()
    scientific_name_lower = scientific_name.lower().strip() if scientific_name else ""
    
    # Strategy 1: Exact match on common name (case-insensitive)
    for species in taxonomy:
        com_name = get_com_name(species).lower()
        if com_name == bird_name_lower:
            code = get_species_code_field(species)
            if code:
                return code
    
    # Strategy 2: If scientific name provided, try exact match on scientific name
    if scientific_name_lower:
        for species in taxonomy:
            sci_name = get_sci_name(species).lower()
            if sci_name == scientific_name_lower:
                code = get_species_code_field(species)
                if code:
                    return code
    
    # Strategy 3: Partial match - prefer more specific matches (longer names)
    # This helps match "Carolina Wren" instead of just "Wren"
    matches = []
    for species in taxonomy:
        com_name = get_com_name(species).lower()
        if bird_name_lower in com_name or com_name in bird_name_lower:
            code = get_species_code_field(species)
            if code:
                matches.append((len(com_name), code, com_name))
    
    # Sort by length (longer = more specific) and return the most specific match
    if matches:
        matches.sort(reverse=True, key=lambda x: x[0])
        return matches[0][1]
    
    # Strategy 4: Try matching scientific name partially if provided
    if scientific_name_lower:
        for species in taxonomy:
            sci_name = get_sci_name(species).lower()
            # Match genus or full scientific name
            if scientific_name_lower in sci_name or sci_name in scientific_name_lower:
                code = get_species_code_field(species)
                if code:
                    return code
    
    return None


def get_observations_by_coords(
    species_code: str,
    latitude: float,
    longitude: float,
    days_back: int = 30,
    years_back: int = 5
) -> List[Dict]:
    """
    Get observations for a species near given coordinates.
    
    Args:
        species_code: eBird species code
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        days_back: Number of days back from today to include
        years_back: Number of years back for same month observations
    
    Returns:
        List of observation dictionaries
    """
    if not species_code:
        return []
    
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        print(f"Invalid coordinates: lat={latitude}, lng={longitude}")
        return []
    
    try:
        api_key = get_ebird_api_key()
    except ValueError as e:
        print(f"API key configuration error: {str(e)}")
        return []
    
    url = f"{EBIRD_API_BASE_URL}/data/obs/geo/recent/{species_code}"
    headers = {
        "X-eBirdApiToken": api_key
    }
    
    params = {
        "lat": latitude,
        "lng": longitude,
        "dist": 50,  # 50km radius
        "back": days_back,
        "maxResults": 10000
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        observations = response.json()
        
        # Filter observations by date range
        today = datetime.now()
        filtered_obs = []
        
        for obs in observations:
            obs_date_str = obs.get("obsDt", "")
            if not obs_date_str:
                continue
            
            try:
                # Parse date (format: YYYY-MM-DD or YYYY-MM-DD HH:MM)
                obs_date = datetime.strptime(obs_date_str.split()[0], "%Y-%m-%d")
                
                # Include if within days_back days
                days_diff = (today - obs_date).days
                if days_diff <= days_back:
                    filtered_obs.append(obs)
                # Or if same month in previous years
                elif years_back > 0 and obs_date.month == today.month:
                    years_diff = today.year - obs_date.year
                    if 1 <= years_diff <= years_back:
                        filtered_obs.append(obs)
            
            except ValueError:
                # Skip observations with invalid date format
                continue
        
        return filtered_obs
    
    except requests.exceptions.Timeout:
        print(f"eBird API request timed out for {species_code}")
        return []
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("Invalid eBird API key")
        elif e.response.status_code == 429:
            print("eBird API rate limit exceeded")
        elif e.response.status_code == 404:
            # Species not found in this location - this is normal
            return []
        else:
            print(f"eBird API error (HTTP {e.response.status_code}) for {species_code}: {str(e)}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching observations for {species_code}: {str(e)}")
        return []
    except Exception as e:
        print(f"Unexpected error in get_observations_by_coords: {str(e)}")
        return []


def get_observations_by_region(
    species_code: str,
    region_code: str,
    days_back: int = 30,
    years_back: int = 5
) -> List[Dict]:
    """
    Get observations for a species in a region.
    
    Args:
        species_code: eBird species code
        region_code: eBird region code (e.g., "US-NY", "US-CA")
        days_back: Number of days back from today to include
        years_back: Number of years back for same month observations
    
    Returns:
        List of observation dictionaries
    """
    if not species_code or not region_code:
        return []
    
    try:
        api_key = get_ebird_api_key()
    except ValueError as e:
        print(f"API key configuration error: {str(e)}")
        return []
    
    url = f"{EBIRD_API_BASE_URL}/data/obs/{region_code}/recent/{species_code}"
    headers = {
        "X-eBirdApiToken": api_key
    }
    
    params = {
        "back": days_back,
        "maxResults": 10000
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        observations = response.json()
        
        # Filter observations by date range (same logic as coords)
        today = datetime.now()
        filtered_obs = []
        
        for obs in observations:
            obs_date_str = obs.get("obsDt", "")
            if not obs_date_str:
                continue
            
            try:
                obs_date = datetime.strptime(obs_date_str.split()[0], "%Y-%m-%d")
                
                days_diff = (today - obs_date).days
                if days_diff <= days_back:
                    filtered_obs.append(obs)
                elif years_back > 0 and obs_date.month == today.month:
                    years_diff = today.year - obs_date.year
                    if 1 <= years_diff <= years_back:
                        filtered_obs.append(obs)
            
            except ValueError:
                continue
        
        return filtered_obs
    
    except requests.exceptions.Timeout:
        print(f"eBird API request timed out for {species_code} in {region_code}")
        return []
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("Invalid eBird API key")
        elif e.response.status_code == 429:
            print("eBird API rate limit exceeded")
        elif e.response.status_code == 404:
            # Species not found in this region - this is normal
            return []
        else:
            print(f"eBird API error (HTTP {e.response.status_code}) for {species_code} in {region_code}: {str(e)}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching observations for {species_code} in {region_code}: {str(e)}")
        return []
    except Exception as e:
        print(f"Unexpected error in get_observations_by_region: {str(e)}")
        return []


def calculate_probabilities(
    bird_suggestions: List,
    location: Dict,
    days_back: int = 30,
    years_back: int = 5
) -> Dict[str, float]:
    """
    Calculate observation probabilities for bird suggestions based on eBird data.
    
    Args:
        bird_suggestions: List of bird species names (strings) or dicts with 'common_name' and 'scientific_name'
        location: Dictionary with 'type' ('coords' or 'region') and location data
        days_back: Number of days back to include
        years_back: Number of years back for same month
    
    Returns:
        Dictionary mapping bird names to probability percentages
    
    Raises:
        ValueError: If location dictionary is invalid
    """
    if not bird_suggestions:
        return {}
    
    if not location or "type" not in location:
        raise ValueError("Invalid location dictionary. Must have 'type' key.")
    
    observation_counts = {}
    
    # Handle both string format (backward compatibility) and dict format
    bird_list = []
    for bird in bird_suggestions:
        if isinstance(bird, dict):
            bird_list.append(bird)
        else:
            bird_list.append({"common_name": str(bird), "scientific_name": ""})
    
    for bird_dict in bird_list:
        bird_name = bird_dict.get("common_name", "")
        scientific_name = bird_dict.get("scientific_name", "")
        
        if not bird_name or not bird_name.strip():
            observation_counts[bird_name] = 0
            continue
        
        # Get species code (try with scientific name if available)
        species_code = get_species_code(bird_name, scientific_name)
        if not species_code:
            observation_counts[bird_name] = 0
            continue
        
        # Get observations based on location type
        if location["type"] == "coords":
            observations = get_observations_by_coords(
                species_code,
                location["latitude"],
                location["longitude"],
                days_back,
                years_back
            )
        elif location["type"] == "region":
            observations = get_observations_by_region(
                species_code,
                location["region_code"],
                days_back,
                years_back
            )
        else:
            observation_counts[bird_name] = 0
            continue
        
        observation_counts[bird_name] = len(observations)
    
    # Calculate probabilities
    total_observations = sum(observation_counts.values())
    
    probabilities = {}
    for bird_name, count in observation_counts.items():
        if total_observations > 0:
            probabilities[bird_name] = (count / total_observations) * 100
        else:
            probabilities[bird_name] = 0.0
    
    return probabilities

