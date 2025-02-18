#!/usr/bin/env python3
"""
This script aggregates KMZ files (exported via Google Takeout from your Garmin recordings)
by extracting the routes (LineStrings) and then creates a combined KML file.
Each route is drawn as a polygon with a semi-transparent hot pink fill (highlighter style)
and a hot pink outline.

Note:
- The KML file only controls your overlay (the hot pink highlights).
- The underlying base map is provided by Google My Maps or Google Earth and cannot be styled via KML.
- To achieve a light grey, colorless background, import the KML into Google My Maps and select
  an appropriate base map (e.g., "Light" or "Simple").
- Alternatively, you could generate a fully custom static map using the Google Static Maps API with custom
  styling parameters and then overlay your routes programmatically.

Usage:
    python my_uploader.py /path/to/kmz_directory --output combined_routes.kml --upload
"""

import os
import zipfile
import xml.etree.ElementTree as ET
import simplekml
import argparse

# --- Step 1. Parse a KMZ file to extract routes from its KML ---
def parse_kmz(kmz_path):
    """
    Opens a KMZ file, finds the first KML inside it, and returns a list of routes.
    Each route is represented as a list of (lon, lat) tuples.
    """
    routes = []
    try:
        with zipfile.ZipFile(kmz_path, 'r') as kmz:
            # Find the KML file inside (commonly "doc.kml")
            kml_filename = None
            for file in kmz.namelist():
                if file.lower().endswith('.kml'):
                    kml_filename = file
                    break
            if not kml_filename:
                print(f"Warning: No KML file found in {kmz_path}")
                return routes
            kml_data = kmz.read(kml_filename)
    except Exception as e:
        print(f"Error reading {kmz_path}: {e}")
        return routes

    # Parse the KML. (KML files usually use the namespace http://www.opengis.net/kml/2.2)
    try:
        root = ET.fromstring(kml_data)
    except Exception as e:
        print(f"Error parsing KML in {kmz_path}: {e}")
        return routes

    namespace = {'kml': 'http://www.opengis.net/kml/2.2'}
    # Look for any Placemark with a LineString element
    for placemark in root.findall('.//kml:Placemark', namespace):
        for ls in placemark.findall('.//kml:LineString', namespace):
            coords_elem = ls.find('kml:coordinates', namespace)
            if coords_elem is None or not coords_elem.text:
                continue
            coords_text = coords_elem.text.strip()
            # KML coordinates are in the format "lon,lat,alt lon,lat,alt ..." (altitude is optional)
            coords = []
            for coord in coords_text.split():
                parts = coord.split(',')
                if len(parts) >= 2:
                    try:
                        lon = float(parts[0])
                        lat = float(parts[1])
                        coords.append((lon, lat))
                    except ValueError:
                        continue
            if coords:
                routes.append(coords)
    return routes

# --- Step 2. Aggregate routes from all KMZ files in a directory ---
def aggregate_routes_from_directory(directory):
    """
    Iterates over all KMZ files in the directory and returns a list of routes.
    Each route is a dict with a 'name' and its coordinate list.
    """
    all_routes = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.kmz'):
            kmz_path = os.path.join(directory, filename)
            routes = parse_kmz(kmz_path)
            if routes:
                for route in routes:
                    all_routes.append({'name': os.path.splitext(filename)[0], 'coords': route})
    return all_routes

# --- Step 3. (Helper) Ensure that the route is "closed" for filling ---
def close_route_if_needed(coords):
    """
    If the first and last coordinates are not the same (within a small tolerance),
    append the first coordinate to the end so the polygon can be filled.
    """
    if not coords:
        return coords
    first = coords[0]
    last = coords[-1]
    if abs(first[0] - last[0]) > 1e-6 or abs(first[1] - last[1]) > 1e-6:
        coords.append(first)
    return coords

# --- Step 4. Create a combined KML file with filled polygons for each route ---
def create_combined_kml(routes, output_file):
    """
    Uses the simplekml library to create a KML file in which each route is drawn as
    a polygon with a semi-transparent hot pink fill (highlighter style) and a hot pink outline.
    
    The hot pink color is based on the hex code for hot pink (#FF69B4), which in KML's
    AABBGGRR format becomes "ffb469ff". Adjust the alpha value for desired transparency.
    """
    kml = simplekml.Kml()
    for route in routes:
        coords = route['coords']
        coords = close_route_if_needed(coords)
        pol = kml.newpolygon(name=route['name'])
        pol.outerboundaryis = coords

        # Set a semi-transparent hot pink fill.
        # The color is given in KML's AABBGGRR format.
        # For hot pink (#FF69B4), the value is "ffb469ff".
        pol.style.polystyle.color = simplekml.Color.changealphaint(100, "ffb469ff")
        pol.style.polystyle.fill = 1

        # Set the outline style to hot pink with a width of 2.
        pol.style.linestyle.color = "ffb469ff"
        pol.style.linestyle.width = 2
    kml.save(output_file)
    print(f"Combined KML saved to {output_file}")

# --- Step 5. (Optional) Upload the KML file to Google Drive ---
def upload_to_drive(file_path, file_name):
    """
    Uploads the given file to Google Drive.
    
    You must have a valid credentials.json (from Google Cloud Console)
    in the working directory. This function will store your OAuth tokens in token.pickle.
    """
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    import pickle

    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no valid credentials, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': file_name, 'mimeType': 'application/vnd.google-earth.kml+xml'}
    media = MediaFileUpload(file_path, mimetype='application/vnd.google-earth.kml+xml')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"File uploaded to Google Drive with ID: {file.get('id')}")
    print("You can now import this KML into Google My Maps.")

# --- Main entry point ---
def main():
    parser = argparse.ArgumentParser(
        description="Generate a combined KML from KMZ files and optionally upload it to Google Drive (for Google My Maps)."
    )
    parser.add_argument("directory", help="Directory containing your KMZ files")
    parser.add_argument("--output", default="combined_routes.kml", help="Output KML filename")
    parser.add_argument("--upload", action="store_true", help="Upload the resulting KML to Google Drive")
    args = parser.parse_args()

    routes = aggregate_routes_from_directory(args.directory)
    if not routes:
        print("No routes found in the directory.")
        return

    create_combined_kml(routes, args.output)

    if args.upload:
        upload_to_drive(args.output, os.path.basename(args.output))

if __name__ == "__main__":
    main()

