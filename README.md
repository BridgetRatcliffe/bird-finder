# Bird Finder 

A Streamlit application that helps identify birds based on user descriptions using Mistral AI and eBird observation data.

## Features

- **AI-Powered Identification**: Uses Mistral AI to generate top 5 bird species suggestions from user descriptions
- **Location-Based Probabilities**: Calculates observation probabilities using eBird API data based on location and time of year
- **Flexible Location Input**: Supports coordinates, city/state/country, or current location
- **Customizable Date Ranges**: Adjustable search windows for recent observations and historical same-month data

## Usage

1. **Describe the bird**: Enter a detailed description including size, colors, beak shape, behavior, etc.

2. **Specify location**: Choose one of:
   - **Coordinates**: Enter latitude and longitude
   - **City/State/Country**: Enter a location string (e.g., "New York, NY, USA")
   - **Current Location**: Use browser geolocation (requires JavaScript)

3. **Adjust settings** (optional): In the sidebar, customize:
   - Days back: How many recent days to include (default: 30)
   - Years back: How many years of same-month data to include (default: 5)

4. **Click "Identify Bird"**: The app will:
   - Use Mistral AI to suggest top 5 bird species
   - Query eBird for observation data in your location
   - Calculate probabilities based on observation frequency

5. **Review results**: See the top 5 suggestions ranked by likelihood. Click on the bird name to be taken to ebird.org to confirm which is your bird!

### No Results Found
- Try a more detailed bird description
- Adjust the date range settings in the sidebar
- Verify your location is correct
- Some rare birds may not have observations in certain areas

### Geocoding Issues
- Try different location formats (e.g., "New York, NY" vs "New York City")
- Use coordinates directly if geocoding fails
- Check your internet connection

## Project Structure

```
bird-finder/
├── app.py                 # Main Streamlit application
├── mistral_client.py      # Mistral AI API integration
├── ebird_client.py        # eBird API integration
├── config.py             # Configuration and API key management
├── requirements.txt      # Python dependencies
├── .streamlit/
│   ├── secrets.toml.example  # Template for Streamlit Cloud secrets
│   └── config.toml       # Streamlit app configuration
├── .env.example         # Template for local environment variables
├── .gitignore          # Git ignore file
└── README.md           # This file
```

## License

This project is open source and available for personal and educational use.

## Acknowledgments

- Mistral AI for the language model API
- eBird for bird observation data
- Streamlit for the web framework

