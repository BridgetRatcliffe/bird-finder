"""
Mistral AI API client for bird identification.
Uses Mistral AI API to generate top 5 bird species suggestions from user descriptions.
"""
import requests
import json
import re
from typing import List, Dict, Tuple
from datetime import datetime
from config import get_mistral_api_key

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"


def get_bird_suggestions(
    description: str,
    location_info: str = "",
    date_info: str = ""
) -> Dict:
    """
    Call Mistral API to generate top 5 bird species suggestions based on description.
    
    Args:
        description: User's description of the bird they saw
        location_info: Location context (e.g., "New York, USA" or coordinates)
        date_info: Date context (e.g., "December 2024")
    
    Returns:
        Dictionary with 'suggestions' (list of dicts with 'common_name' and 'scientific_name') 
        and 'model_used' (string)
    
    Raises:
        ValueError: If description is empty
        Exception: If API call fails or response cannot be parsed
    """
    if not description or not description.strip():
        raise ValueError("Bird description cannot be empty")
    
    try:
        api_key = get_mistral_api_key()
    except ValueError as e:
        raise Exception(f"API key configuration error: {str(e)}")
    
    # Build context string
    context_parts = []
    if location_info:
        context_parts.append(f"Location: {location_info}")
    if date_info:
        context_parts.append(f"Date: {date_info}")
    context_str = "\n".join(context_parts) if context_parts else ""
    
    # Create a structured prompt that asks for specific bird species
    prompt = f"""You are an expert ornithologist. Based on the bird description below, identify the top 5 most likely SPECIFIC bird species.

IMPORTANT: Return SPECIFIC species names, not generic groups. For example:
- Use "Carolina Wren" NOT just "Wren"
- Use "American Robin" NOT just "Robin"
- Use "Northern Cardinal" NOT just "Cardinal"
- Use "Blue Jay" NOT just "Jay"

Return your response in this EXACT format (one species per line):
1. Common Name | Scientific Name
2. Common Name | Scientific Name
3. Common Name | Scientific Name
4. Common Name | Scientific Name
5. Common Name | Scientific Name

Bird Description: {description}
{context_str}

Top 5 bird species:"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Try different models - fallback to mistral-tiny if open-mixtral fails
    models_to_try = ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest", "mistral-tiny"]
    
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2,  # Lower temperature for more consistent, specific results
            "max_tokens": 300
        }
        
        try:
            response = requests.post(MISTRAL_API_URL, headers=headers, json=payload, timeout=30)
            
            # If we get a 404 or 400, try next model
            if response.status_code == 404 or response.status_code == 400:
                continue
            
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            # Parse the structured response
            bird_suggestions = parse_structured_bird_suggestions(content)
            
            # If we got valid results, return them with model name
            if bird_suggestions and len(bird_suggestions) > 0:
                # Ensure we have exactly 5 suggestions
                while len(bird_suggestions) < 5:
                    bird_suggestions.append({"common_name": "", "scientific_name": ""})
                # Return suggestions with model info
                return {
                    "suggestions": bird_suggestions[:5],
                    "model_used": model
                }
            
        except requests.exceptions.HTTPError as e:
            # If it's a model-specific error, try next model
            if e.response.status_code in [404, 400]:
                continue
            raise
        except Exception as e:
            # If this is the last model, raise the error
            if model == models_to_try[-1]:
                raise Exception(f"Failed to get valid response from any model: {str(e)}")
            continue
    
    raise Exception("Could not get valid response from any Mistral model")
    
    try:
        response = requests.post(MISTRAL_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        
        # Parse the response to extract bird names
        bird_suggestions = parse_bird_suggestions(content)
        
        # Ensure we have exactly 5 suggestions
        if len(bird_suggestions) < 5:
            # If we got fewer than 5, pad with empty strings or try to extract more
            bird_suggestions.extend([""] * (5 - len(bird_suggestions)))
        elif len(bird_suggestions) > 5:
            # If we got more than 5, take only the first 5
            bird_suggestions = bird_suggestions[:5]
        
        return bird_suggestions
    
    except requests.exceptions.Timeout:
        raise Exception("Mistral API request timed out. Please try again.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise Exception("Invalid Mistral API key. Please check your API key.")
        elif e.response.status_code == 429:
            raise Exception("Mistral API rate limit exceeded. Please wait a moment and try again.")
        else:
            raise Exception(f"Mistral API error (HTTP {e.response.status_code}): {str(e)}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to call Mistral API: {str(e)}")
    except (KeyError, IndexError) as e:
        raise Exception(f"Failed to parse Mistral API response: {str(e)}")
    except ValueError as e:
        raise e  # Re-raise ValueError from validation
    except Exception as e:
        raise Exception(f"Unexpected error calling Mistral API: {str(e)}")


def parse_structured_bird_suggestions(content: str) -> List[Dict[str, str]]:
    """
    Parse the Mistral API response to extract structured bird species information.
    
    Args:
        content: Raw response content from Mistral API
    
    Returns:
        List of dictionaries with 'common_name' and 'scientific_name' keys
    """
    birds = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Skip lines that are clearly not species entries
        if any(skip in line.lower() for skip in ['description:', 'location:', 'date:', 'top 5', 'important:']):
            continue
        
        # Try to parse format: "1. Common Name | Scientific Name"
        # Remove numbering first
        line_clean = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
        
        # Split by pipe separator
        if '|' in line_clean:
            parts = [p.strip() for p in line_clean.split('|')]
            if len(parts) >= 2:
                common_name = parts[0].strip()
                scientific_name = parts[1].strip()
                
                # Clean up common name (remove extra punctuation)
                common_name = re.sub(r'[^\w\s-]', '', common_name).strip()
                
                # Clean up scientific name (should be Genus species format)
                scientific_name = re.sub(r'[^\w\s]', '', scientific_name).strip()
                
                if common_name and len(common_name) > 2:
                    birds.append({
                        "common_name": common_name,
                        "scientific_name": scientific_name
                    })
                    continue
        
        # Fallback: try to extract just common name if pipe format not found
        # Remove numbering and common prefixes
        line_clean = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
        
        # Try to extract common name (everything before first comma, colon, or dash)
        common_name = re.split(r'[,:;]', line_clean)[0].strip()
        common_name = re.sub(r'[^\w\s-]', '', common_name).strip()
        
        # Skip if it's too short or looks like instructions
        if common_name and len(common_name) > 2 and not any(
            skip in common_name.lower() for skip in ['format', 'example', 'important', 'return']
        ):
            birds.append({
                "common_name": common_name,
                "scientific_name": ""  # Will try to look up later
            })
    
    return birds[:5]  # Return at most 5 birds

