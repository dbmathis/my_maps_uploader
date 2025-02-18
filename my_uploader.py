#!/usr/bin/env python3
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
import simplekml
import argparse

def natural_sort_key(s):
    """Return a list of string and number chunks for natural sorting."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split('(\d+)', s)]

def parse_kmz(kmz_path):
    """
    Opens a KMZ file, extracts the KML, and attempts to parse a <TimeStamp>/<when> element.
    If not found, it tries to parse a <TimeSpan>/<begin> element.
    Returns a tuple (timestamp, routes) where timestamp is a datetime object (or None)
    and routes is a list of coordinate lists.
    """
    routes = []
    timestamp = None
    try:
        with zipfile.ZipFile(kmz_path, 'r') as kmz:
            # Look for a file ending with .kml (commonly "doc.kml")
            kml_filename = next((f for f in kmz.namelist() if f.lower().endswith('.kml')), None)
            if not kml_filename:
                print(f"Warning: No KML file found in {kmz_path}")
                return None, routes
            kml_data = kmz.read(kml_filename)
    except Exception as e:
        print(f"Error reading {kmz_path}: {e}")
        return None, routes

    try:
        root = ET.fromstring(kml_data)
    except Exception as e:
        print(f"Error parsing KML in {kmz_path}: {e}")
        return None, routes

    namespace = {'kml': 'http://www.opengis.net/kml/2.2'}

    # Try to extract a timestamp from <TimeStamp>/<when>
    time_elem = root.find('.//kml:TimeStamp/kml:when', namespace)
    if time_elem is not None and time_elem.text:
        try:
            timestamp = datetime.fromisoformat(time_elem.text.replace("Z", "+00:00"))
        except Exception as e:
            print(f"Error parsing timestamp in {kmz_path}: {e}")
            timestamp = None
    else:
        # Fallback: try <TimeSpan>/<begin>
        timespan_elem = root.find('.//kml:TimeSpan/kml:begin', namespace)
        if timespan_elem is not None and timespan_elem.text:
            try:
                timestamp = datetime.fromisoformat(timespan_elem.text.replace("Z", "+00:00"))
            except Exception as e:
                print(f"Error parsing timespan begin in {kmz_path}: {e}")
                timestamp = None

    # Extract routes from <Placemark>/<LineString>/<coordinates>
    for placemark in root.findall('.//kml:Placemark', namespace):
        for ls in placemark.findall('.//kml:LineString', namespace):
            coords_elem = ls.find('kml:coordinates', namespace)
            if coords_elem is None or not coords_elem.text:
                continue
            coords_text = coords_elem.text.strip()
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
    return timestamp, routes

def close_route_if_needed(coords):
    """
    Ensures the route is "closed" (i.e., the first coordinate equals the last).
    """
    if coords and (coords[0] != coords[-1]):
        coords.append(coords[0])
    return coords

def aggregate_routes_from_directory(directory):
    """
    Iterates over all KMZ files in the directory, extracts routes along with
    their recording date (parsed from within the file), and returns a list of routes.
    The routes are sorted by file name using natural sort (so numeric parts sort correctly).
    """
    all_routes = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.kmz'):
            kmz_path = os.path.join(directory, filename)
            timestamp, routes = parse_kmz(kmz_path)
            if routes:
                for route in routes:
                    all_routes.append({
                        'name': os.path.splitext(filename)[0],
                        'date': timestamp,  # May be None if not found
                        'coords': route
                    })
    # Sort routes by file name using natural sort (ignoring case)
    all_routes.sort(key=lambda r: natural_sort_key(r['name']))
    return all_routes

def create_combined_kml(routes, output_file):
    """
    Uses simplekml to create a combined KML file.
    Each route is drawn as a polygon with a hot pink fill and outline.
    The fill is semi-transparent while the outline is fully opaque.
    The route name is prefixed with the recording date in YYYYMMDD format if available.
    """
    kml = simplekml.Kml()
    for route in routes:
        coords = close_route_if_needed(route['coords'])
        if route['date']:
            date_prefix = route['date'].strftime('%Y%m%d')
            route_name = f"{date_prefix} {route['name']}"
        else:
            route_name = route['name']
        pol = kml.newpolygon(name=route_name)
        pol.outerboundaryis = coords
        fill_color = simplekml.Color.changealphaint(100, simplekml.Color.hotpink)
        pol.style.polystyle.color = fill_color
        pol.style.polystyle.fill = 1
        pol.style.linestyle.color = simplekml.Color.hotpink
        pol.style.linestyle.width = 2
    kml.save(output_file)
    print(f"Combined KML saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Aggregate KMZ files and generate a combined KML sorted by file name (natural order)."
    )
    parser.add_argument("directory", help="Directory containing KMZ files")
    parser.add_argument("--output", default="combined_routes.kml", help="Output KML filename")
    args = parser.parse_args()

    routes = aggregate_routes_from_directory(args.directory)
    if not routes:
        print("No routes found in the directory.")
        return

    create_combined_kml(routes, args.output)

if __name__ == "__main__":
    main()
