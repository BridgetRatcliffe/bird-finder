"""
Bird Finder - Streamlit Application
Identifies birds based on user descriptions using Mistral AI and eBird API.
"""
import streamlit as st
from datetime import datetime
from typing import List, Dict
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

from mistral_client import get_bird_suggestions
from ebird_client import calculate_probabilities
from config import DEFAULT_DAYS_BACK, DEFAULT_YEARS_BACK


def calculate_combined_scores(
    bird_suggestions: List[Dict],
    ebird_probabilities: Dict[str, float],
    llm_ranks: Dict[str, int],
    llm_weight: float,
    ebird_weight: float
) -> Dict[str, Dict]:
    """
    Calculate combined weighted scores from LLM ranking and eBird probabilities.
    
    Args:
        bird_suggestions: List of bird dictionaries with common_name
        ebird_probabilities: Dictionary mapping bird names to eBird probabilities (0-100)
        llm_ranks: Dictionary mapping bird names to LLM ranks (1-5, where 1 is best)
        llm_weight: Weight for LLM ranking (0-1)
        ebird_weight: Weight for eBird probability (0-1)
    
    Returns:
        Dictionary mapping bird names to score data including combined_score, llm_score, ebird_probability
    """
    combined_scores = {}
    
    for bird_dict in bird_suggestions:
        common_name = bird_dict.get("common_name", "")
        if not common_name:
            continue
        
        # Get LLM rank (1-5, where 1 is best)
        llm_rank = llm_ranks.get(common_name, 5)  # Default to worst rank if not found
        
        # Convert LLM rank to score (rank 1 = 1.0, rank 5 = 0.2)
        # Formula: (6 - rank) / 5
        llm_score = (6 - llm_rank) / 5.0
        
        # Get eBird probability (already 0-100, normalize to 0-1)
        ebird_prob = ebird_probabilities.get(common_name, 0.0)
        ebird_score = ebird_prob / 100.0
        
        # Calculate combined score
        combined_score = (llm_score * llm_weight) + (ebird_score * ebird_weight)
        
        # Normalize to 0-100 for display
        combined_score_percent = combined_score * 100.0
        
        combined_scores[common_name] = {
            "combined_score": combined_score_percent,
            "llm_rank": llm_rank,
            "llm_score": llm_score * 100.0,  # For display
            "ebird_probability": ebird_prob,
            "ebird_score": ebird_score * 100.0  # For display
        }
    
    return combined_scores

# Try to import geolocation component
try:
    from streamlit_geolocation import streamlit_geolocation
    HAS_GEOLOCATION = True
except ImportError:
    HAS_GEOLOCATION = False

# Page configuration
st.set_page_config(
    page_title="Bird Finder",
    # page_icon="🐦",
    layout="wide"
)

# Initialize geocoder
@st.cache_data
def geocode_location(location_string: str):
    """Geocode a location string to coordinates."""
    try:
        geolocator = Nominatim(user_agent="bird_finder_app")
        location = geolocator.geocode(location_string, timeout=10)
        if location:
            return location.latitude, location.longitude
        return None, None
    except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
        st.error(f"Geocoding error: {str(e)}")
        return None, None


def main():
    st.title("Bird Finder")
    st.markdown("Describe a bird you saw, and we'll identify it using AI and eBird observation data!")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")
        days_back = st.number_input(
            "Days back to include",
            min_value=1,
            max_value=365,
            value=DEFAULT_DAYS_BACK,
            help="Number of recent days to include in observation search"
        )
        years_back = st.number_input(
            "Years back (same month)",
            min_value=0,
            max_value=10,
            value=DEFAULT_YEARS_BACK,
            help="Number of years back to include observations from the same month"
        )
        
        st.markdown("---")
        st.subheader("Ranking Weights")
        st.caption("Adjust how much LLM vs eBird data influences the final ranking (weights automatically sum to 1.0)")
        
        # Initialize session state for weights if not exists
        if 'llm_weight_raw' not in st.session_state:
            st.session_state.llm_weight_raw = 0.4
            st.session_state.ebird_weight_raw = 0.6
        
        # Use a single slider for LLM weight, eBird weight is automatically 1 - llm_weight
        llm_weight_raw = st.slider(
            "LLM Description Match Weight",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.llm_weight_raw,
            step=0.05,
            help="Weight for how well the bird matches your description (from AI). eBird weight is automatically set to complement this.",
            key="llm_weight_slider"
        )
        
        # Update session state
        st.session_state.llm_weight_raw = llm_weight_raw
        ebird_weight_raw = 1.0 - llm_weight_raw
        st.session_state.ebird_weight_raw = ebird_weight_raw
        
        # Display the actual weights being used (they already sum to 1.0)
        st.caption(f"**Current weights:** LLM = {llm_weight_raw:.2f} ({llm_weight_raw*100:.0f}%), eBird = {ebird_weight_raw:.2f} ({ebird_weight_raw*100:.0f}%)")
        
        # Use normalized weights (they already sum to 1.0)
        llm_weight = llm_weight_raw
        ebird_weight = ebird_weight_raw
    
    # Main input section
    st.header("Describe Your Bird")
    description = st.text_area(
        "What did the bird look like? Include details like size, color, beak shape, behavior, etc.",
        height=150,
        placeholder="Example: I saw a small bird with a red breast and black head, about the size of a sparrow..."
    )
    
    # Location input section
    st.header("Location")
    location_method = st.radio(
        "How would you like to specify your location?",
        ["Coordinates", "City/State/Country", "Use Current Location"],
        horizontal=True
    )
    
    location = None
    location_type = None
    
    if location_method == "Coordinates":
        col1, col2 = st.columns(2)
        with col1:
            latitude = st.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=40.7987,
                format="%.6f",
                help="Enter latitude coordinate (-90 to 90)"
            )
        with col2:
            longitude = st.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=180.0,
                value=-73.9563,
                format="%.6f",
                help="Enter longitude coordinate (-180 to 180)"
            )
        
        if latitude and longitude:
            location = {
                "type": "coords",
                "latitude": latitude,
                "longitude": longitude
            }
            location_type = "coords"
    
    elif location_method == "City/State/Country":
        location_string = st.text_input(
            "Enter location",
            placeholder="Example: New York, NY, USA or London, UK"
        )
        
        if location_string:
            with st.spinner("Looking up location..."):
                lat, lng = geocode_location(location_string)
            
            if lat and lng:
                st.success(f"Found location: {lat:.4f}, {lng:.4f}")
                location = {
                    "type": "coords",
                    "latitude": lat,
                    "longitude": lng
                }
                location_type = "coords"
            else:
                st.error("Could not find location. Please try a different format.")
    
    else:  # Use Current Location
        if HAS_GEOLOCATION:
            st.info("Click the button below to get your current location.")
            try:
                location_data = streamlit_geolocation()
                
                if location_data:
                    if isinstance(location_data, dict) and 'latitude' in location_data and 'longitude' in location_data:
                        lat = location_data['latitude']
                        lng = location_data['longitude']
                        if lat and lng:
                            st.success(f"📍 Location found: {lat:.4f}, {lng:.4f}")
                            location = {
                                "type": "coords",
                                "latitude": float(lat),
                                "longitude": float(lng)
                            }
                            location_type = "coords"
                        else:
                            st.warning("Invalid location coordinates. Please try again.")
                    else:
                        st.warning("Location data incomplete. Please try again or use coordinates/city.")
                else:
                    st.info("Click the button above to share your location.")
            except Exception as e:
                st.error(f"Error getting location: {str(e)}")
                st.info("Please use coordinates or city/state/country instead.")
        else:
            st.warning(
                "Geolocation component not available. Please install 'streamlit-geolocation' "
                "or use coordinates/city/state/country instead."
            )
    
    # Submit button
    st.markdown("---")
    submit_button = st.button("🔍 Identify Bird", type="primary", use_container_width=True)
    
    # Process request
    if submit_button:
        # Validation
        if not description or not description.strip():
            st.error("Please provide a description of the bird you saw.")
            return
        
        if not location:
            st.error("Please specify your location.")
            return
        
        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Initialize variables for results display
        model_used = "unknown"
        bird_suggestions = []
        
        try:
            # Step 1: Get bird suggestions from Mistral
            status_text.text("Asking AI to identify possible bird species...")
            progress_bar.progress(20)
            
            try:
                # Build location and date context for the LLM
                location_context = ""
                if location["type"] == "coords":
                    location_context = f"Latitude {location['latitude']:.4f}, Longitude {location['longitude']:.4f}"
                elif location["type"] == "region":
                    location_context = location.get("region_code", "")
                
                date_context = datetime.now().strftime("%B %Y")
                
                mistral_result = get_bird_suggestions(
                    description,
                    location_info=location_context,
                    date_info=date_context
                )
                progress_bar.progress(40)
                
                # Extract suggestions and model name
                bird_suggestions = mistral_result.get("suggestions", [])
                model_used = mistral_result.get("model_used", "unknown")
                
                if not bird_suggestions or all(not b.get("common_name") for b in bird_suggestions):
                    st.error("Could not generate bird suggestions. Please try a more detailed description.")
                    return
                
                # Filter out empty suggestions
                bird_suggestions = [b for b in bird_suggestions if b and b.get("common_name")]
                
                if not bird_suggestions:
                    st.error("No valid bird suggestions generated. Please try a more detailed description.")
                    return
                
            except ValueError as e:
                st.error(str(e))
                return
            except Exception as e:
                error_msg = str(e)
                if "API key" in error_msg.lower():
                    st.error(f"API Configuration Error: {error_msg}")
                    st.info("Please check your Mistral API key in `.env` file (local) or Streamlit Cloud secrets.")
                else:
                    st.error(f"Error getting bird suggestions: {error_msg}")
                    st.info("Please try again with a more detailed description.")
                return
            
            # Step 2: Get observation data from eBird
            status_text.text("📊 Analyzing eBird observation data...")
            progress_bar.progress(60)
            
            try:
                # Pass full structured data to calculate_probabilities
                probabilities = calculate_probabilities(
                    bird_suggestions,
                    location,
                    days_back=days_back,
                    years_back=years_back
                )
                progress_bar.progress(80)
                
            except ValueError as e:
                st.error(f"Invalid input: {str(e)}")
                return
            except Exception as e:
                error_msg = str(e)
                if "API key" in error_msg.lower():
                    st.error(f"API Configuration Error: {error_msg}")
                    st.info("Please check your eBird API key in `.env` file (local) or Streamlit Cloud secrets.")
                elif "taxonomy" in error_msg.lower():
                    st.error(f"Error loading bird taxonomy: {error_msg}")
                    st.info("This might be a temporary eBird API issue. Please try again in a moment.")
                    with st.expander("Technical Details"):
                        st.code(str(e))
                else:
                    st.error(f"Error calculating probabilities: {error_msg}")
                    st.info("Please try again or adjust your location settings.")
                return
            
            # Step 3: Calculate combined weighted scores
            status_text.text("📊 Calculating combined scores...")
            progress_bar.progress(90)
            
            # Create mapping of bird names to their LLM ranks (1-5, where 1 is best)
            llm_ranks = {}
            for idx, bird_dict in enumerate(bird_suggestions, 1):
                common_name = bird_dict.get("common_name", "")
                if common_name:
                    llm_ranks[common_name] = idx
            
            # Calculate combined scores
            combined_scores = calculate_combined_scores(
                bird_suggestions,
                probabilities,
                llm_ranks,
                llm_weight,
                ebird_weight
            )
            
            # Step 4: Display results
            status_text.text("✅ Analysis complete!")
            progress_bar.progress(100)
            time.sleep(0.5)  # Brief pause for UX
            progress_bar.empty()
            status_text.empty()
            
            st.markdown("---")
            st.header("Identification Results")
            
            # Sort by combined score (descending)
            sorted_results = sorted(
                combined_scores.items(),
                key=lambda x: x[1]["combined_score"],
                reverse=True
            )
            
            # Display results
            if sum(probabilities.values()) == 0:
                st.warning(
                    "No observations found for these species in your location and time period. "
                    "Results are ranked by description match only.\n\n"
                    "This could mean:\n"
                    "- The birds are rare in this area\n"
                    "- The time period selected has no observations\n"
                    "- The species names may need adjustment"
                )
                st.subheader("Suggested Species (by Description Match):")
                
                # Get species codes for eBird links
                from ebird_client import get_species_code
                for i, bird_dict in enumerate(bird_suggestions, 1):
                    common_name = bird_dict.get("common_name", "")
                    scientific_name = bird_dict.get("scientific_name", "")
                    if common_name:
                        species_code = get_species_code(common_name, scientific_name)
                        if species_code:
                            ebird_url = f"https://ebird.org/species/{species_code}"
                            common_name_link = f"[{common_name}]({ebird_url})"
                        else:
                            common_name_link = common_name
                        
                        if scientific_name:
                            st.write(f"{i}. **{common_name_link}** (*{scientific_name}*)")
                        else:
                            st.write(f"{i}. **{common_name_link}**")
                
                # Display model name at the bottom
                st.markdown("---")
                st.caption(f"🤖 Model used: **{model_used}**")
            else:
                # Match scores with bird suggestions (including scientific names)
                bird_dict_map = {b["common_name"]: b for b in bird_suggestions if b.get("common_name")}
                
                # Get species codes for eBird links
                from ebird_client import get_species_code
                species_codes = {}
                for bird_name in bird_dict_map.keys():
                    bird_dict = bird_dict_map[bird_name]
                    code = get_species_code(
                        bird_dict.get("common_name", ""),
                        bird_dict.get("scientific_name", "")
                    )
                    if code:
                        species_codes[bird_name] = code
                
                # Create columns for better display
                for i, (bird_name, score_data) in enumerate(sorted_results):
                    if not bird_name or not bird_name.strip():
                        continue
                    
                    bird_dict = bird_dict_map.get(bird_name, {})
                    scientific_name = bird_dict.get("scientific_name", "")
                    combined_score = score_data["combined_score"]
                    ebird_prob = score_data["ebird_probability"]
                    llm_rank = score_data["llm_rank"]
                    species_code = species_codes.get(bird_name, "")
                    
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        # Create eBird link if species code is available
                        if species_code:
                            ebird_url = f"https://ebird.org/species/{species_code}"
                            bird_name_link = f"[{bird_name}]({ebird_url})"
                        else:
                            bird_name_link = bird_name
                        
                        if scientific_name:
                            st.subheader(f"{i+1}. {bird_name_link}")
                            st.caption(f"*{scientific_name}*")
                        else:
                            st.subheader(f"{i+1}. {bird_name_link}")
                    with col2:
                        st.metric("Combined Score", f"{combined_score:.1f}")
                    with col3:
                        with st.expander("Details"):
                            st.write(f"**LLM Rank:** {llm_rank} (score: {score_data['llm_score']:.1f})")
                            st.write(f"**eBird Prob:** {ebird_prob:.1f}")
                            st.write(f"**Weights Used:** LLM={llm_weight:.2f} ({llm_weight*100:.0f}%), eBird={ebird_weight:.2f} ({ebird_weight*100:.0f}%)")
                            st.write(f"**Calculation:** ({score_data['llm_score']:.1f} × {llm_weight:.2f}) + ({ebird_prob:.1f} × {ebird_weight:.2f}) = {combined_score:.1f}")
                            if species_code:
                                st.write(f"**eBird Page:** [View on eBird](https://ebird.org/species/{species_code})")
                    
                    # Progress bar for visual representation
                    st.progress(combined_score / 100.0)
                    st.markdown("---")
                
                # Display model name at the bottom
                st.markdown("---")
                st.caption(f"🤖 Model used: **{model_used}**")
        
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
            st.info("Please try again. If the problem persists, check your API keys and network connection.")
            import traceback
            with st.expander("Error Details"):
                st.code(traceback.format_exc())
        
        finally:
            progress_bar.empty()
            status_text.empty()


if __name__ == "__main__":
    main()

