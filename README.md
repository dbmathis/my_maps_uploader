# My Uploader

A Python script to aggregate KMZ files from Garmin recordings, extract routes, and generate a KML file with hot pink, semi-transparent overlays for Google My Maps. An optional feature allows uploading the KML directly to Google Drive.

## Features
- Aggregates routes from multiple KMZ files
- Applies hot pink, semi-transparent styling to routes
- Optionally uploads the KML to Google Drive
- (Optional) Merges new routes with existing data using a JSON store

## Requirements
- Python 3.x
- Packages:
  - simplekml
  - google-api-python-client
  - google-auth-httplib2
  - google-auth-oauthlib  
(For the upload feature, obtain OAuth2 credentials via Google’s Drive API Quickstart and place `credentials.json` in the directory.)

## Installation
1. Clone the repository:
   git clone https://github.com/yourusername/my-uploader.git
   cd my-uploader
2. Install the required packages:
   pip3 install simplekml google-api-python-client google-auth-httplib2 google-auth-oauthlib

## Usage
- Generate a Combined KML:
  python3 my_uploader.py '/path/to/kmz_directory' --output my_walks.kml

- Generate and Upload KML to Google Drive:
  python3 my_uploader.py '/path/to/kmz_directory' --output my_walks.kml --upload

## Importing into Google My Maps
1. Open [Google My Maps](https://www.google.com/mymaps)
2. Create a new map and click "Import" to upload your `my_walks.kml`
3. Choose a light/grey base map (e.g., "Light" or "Simple") so the hot pink overlays stand out

## License
MIT License

## Contributing
Contributions, suggestions, and bug reports are welcome—please open an issue or submit a pull request.

## Contact
For questions or feedback, open an issue in this repository or contact the maintainer directly.
