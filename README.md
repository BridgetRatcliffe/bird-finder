# Bird Finder 🐦

A Streamlit application that helps identify birds based on user descriptions using Mistral AI and eBird observation data.

## Features

- **AI-Powered Identification**: Uses Mistral AI to generate top 5 bird species suggestions from user descriptions
- **Location-Based Probabilities**: Calculates observation probabilities using eBird API data based on location and time of year
- **Flexible Location Input**: Supports coordinates, city/state/country, or current location
- **Customizable Date Ranges**: Adjustable search windows for recent observations and historical same-month data

## Setup

### Prerequisites

- Python 3.8 or higher
- Mistral AI API key (free tier available at https://console.mistral.ai/)
- eBird API key (free, available at https://ebird.org/api/keygen)

### Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up API keys:

   **For local development:**
   - Copy `.env.example` to `.env`
   - Add your API keys to `.env`:
   ```
   MISTRAL_API_KEY=your_mistral_api_key_here
   EBIRD_API_KEY=your_ebird_api_key_here
   ```

   **For Streamlit Cloud deployment:**
   - Add your API keys via the Streamlit Cloud dashboard
   - Or create `.streamlit/secrets.toml` (see `.streamlit/secrets.toml.example`)

### Running Locally

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

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

5. **Review results**: See the top 5 suggestions ranked by probability

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

## API Keys

### Mistral AI
1. Sign up at https://console.mistral.ai/
2. Navigate to API keys section
3. Create a new API key
4. Copy the key to your `.env` file or Streamlit Cloud secrets

### eBird
1. Visit https://ebird.org/api/keygen
2. Log in with your eBird account (create one if needed)
3. Generate an API key
4. Copy the key to your `.env` file or Streamlit Cloud secrets

## Deployment to Streamlit Cloud

1. Push your code to a GitHub repository
2. Go to https://share.streamlit.io/
3. Sign in with your GitHub account
4. Click "New app"
5. Select your repository and branch
6. Set the main file path to `app.py`
7. Add your API keys in the "Secrets" section:
   ```
   MISTRAL_API_KEY=your_key_here
   EBIRD_API_KEY=your_key_here
   ```
8. Click "Deploy"

## Troubleshooting

### API Key Errors
- Ensure your API keys are correctly set in `.env` (local) or Streamlit Cloud secrets
- Check that API keys are valid and have not expired
- Verify you're using the correct key format (no extra spaces or quotes)

### No Results Found
- Try a more detailed bird description
- Adjust the date range settings in the sidebar
- Verify your location is correct
- Some rare birds may not have observations in certain areas

### Geocoding Issues
- Try different location formats (e.g., "New York, NY" vs "New York City")
- Use coordinates directly if geocoding fails
- Check your internet connection

## License

This project is open source and available for personal and educational use.

## Acknowledgments

- Mistral AI for the language model API
- eBird for bird observation data
- Streamlit for the web framework

