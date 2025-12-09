"""
Configuration module for Bird Finder app.
Handles loading API keys from Streamlit secrets (for Cloud) or .env file (for local).
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()


def get_api_key(key_name: str) -> str:
    """
    Get API key from Streamlit secrets (Cloud) or environment variable (local).
    
    Args:
        key_name: Name of the API key (e.g., 'MISTRAL_API_KEY', 'EBIRD_API_KEY')
    
    Returns:
        API key string
    
    Raises:
        ValueError: If API key is not found in either location
    """
    # Try Streamlit secrets first (for Cloud deployment)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key_name in st.secrets:
            return st.secrets[key_name]
    except (ImportError, RuntimeError, AttributeError):
        # Streamlit not available or not in Streamlit context
        pass
    
    # Fall back to environment variable (for local development)
    api_key = os.getenv(key_name)
    if api_key:
        return api_key
    
    # If not found in either location, raise error
    raise ValueError(
        f"API key '{key_name}' not found. "
        f"For local development, set it in .env file. "
        f"For Streamlit Cloud, set it in .streamlit/secrets.toml"
    )


# API Configuration - will be loaded when needed
def get_mistral_api_key() -> str:
    """Get Mistral API key."""
    return get_api_key('MISTRAL_API_KEY')


def get_ebird_api_key() -> str:
    """Get eBird API key."""
    return get_api_key('EBIRD_API_KEY')

# API Endpoints
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
EBIRD_API_BASE_URL = "https://api.ebird.org/v2"

# Default date range settings
DEFAULT_DAYS_BACK = 30
DEFAULT_YEARS_BACK = 5

