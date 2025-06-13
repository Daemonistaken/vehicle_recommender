#-------------------------------------------------------------------------------------------------
# NOTE: All code and documentation are presented in English due to a mandatory language requirement.
# NOTE: Todo el código y la documentación se presentan en inglés debido a una obligación de uso del idioma.
#-------------------------------------------------------------------------------------------------
import os
import time
import json
import csv
import random
import requests
import polyline
import numpy as np
import haversine as hs
from dotenv import load_dotenv
from logger_setup import get_file_logger

# Google Maps API key access required to run this script.
    # Places API
    # Directtions API
    # Maps Elevation API

# Setup environment and logger
load_dotenv()
API = os.getenv("API")
logger = get_file_logger("mapsAPI_")


# Request with Retry/Backoff Strategy to not overwhelm the API
def make_request_with_backoff(url, params, method="GET", max_retries=5):
    delay = 1
    for attempt in range(max_retries):
        try:
            logger.debug(f"[make_request_with_backoff] Attempt {attempt+1}: {method} request to {url} with params: {params}")
            response = requests.get(url, params=params) if method == "GET" else requests.post(url, json=params)
            if response.status_code == 200:
                return response
            elif response.status_code in (429, 500, 503):
                logger.warning(f"Retryable error {response.status_code}, backing off for {delay} seconds")
                time.sleep(delay + random.uniform(0, 0.5))
                delay *= 2
            else:
                logger.error(f"Non-retryable error {response.status_code}: {response.text}")
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Retry {attempt+1}/{max_retries}] Request failed: {e}")
            time.sleep(delay + random.uniform(0, 0.5))
            delay *= 2
    raise RuntimeError("Failed after maximum retries")

# Directions API Handler
# Avoid parameter can be used to avoid the following:
# tolls, highways, ferries, indoor
# Parameter must be formatted as a | separated string, e.g. "tolls|highways|ferries|indoor"
def get_directions(origin, destination, waypoints=None, avoid=None):
    logger.info(f"[get_directions] Getting route from {origin} to {destination} via {waypoints}")
    directions_url = "https://maps.googleapis.com/maps/api/directions/json"
    
    params = {
        "origin": origin,
        "destination": destination,
        "key": API
    }
    #Optional parameters
    if waypoints:
        params["waypoints"] = "|".join(waypoints)
    if avoid:
        if avoid.__contains__(","):
            avoid.replace(",", "|")
            params["avoid"] = avoid
        else:
            params["avoid"] = "|".join(avoid)
    
    response = make_request_with_backoff(directions_url, params)
    data = response.json()
    if data["status"] != "OK":
        raise RuntimeError(f"Directions API error: {data['status']}")
    return data

# Elevation API Handler
def get_elevation(encoded_polyline, samples=50):
    logger.info("[get_elevation] Fetching elevation along route")
    elevation_url = "https://maps.googleapis.com/maps/api/elevation/json"
    params = {
        "path": f"enc:{encoded_polyline}",
        "samples": samples,
        "key": API
    }
    response = make_request_with_backoff(elevation_url, params)
    return [res["elevation"] for res in response.json()["results"]]

# Route Sampling Helper
def sample_route_points(encoded_polyline, total_distance_km, desired_samples=10):
    logger.info("[sample_route_points] Sampling route points for station lookup")
    decoded = polyline.decode(encoded_polyline)
    step_km = max(total_distance_km / desired_samples, 10)
    filtered = [decoded[0]]
    for pt in decoded[1:]:
        if hs.haversine(filtered[-1], pt) >= step_km:
            filtered.append(pt)
    logger.debug(f"[sample_route_points] Sampled {len(filtered)} points (step ~{step_km:.1f} km)")
    return filtered

# Gas Station Fetching
def get_nearby_stations(points):
    logger.info("[get_nearby_stations] Fetching gas stations at sampled points")
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    station_map = {}
    count = 0

    for point, (lat, lng) in enumerate(points):
        logger.debug(f"[get_nearby_stations] Searching point {point} @ {lat},{lng}")
        params = {
            "location": f"{lat},{lng}",
            "radius": 5000,
            "type": "gas_station",
            "key": API
        }
        response = make_request_with_backoff(url, params)
        results = response.json().get("results", [])

        stations = [
            {
                "name": r.get("name"),
                "lat": r["geometry"]["location"]["lat"],
                "lng": r["geometry"]["location"]["lng"],
                "rating": r.get("rating"),
                "vicinity": r.get("vicinity"),
                "place_id": r.get("place_id")
            } for r in results
        ]

        count += len(stations)
        station_map[point] = stations
        time.sleep(1)  # avoid rate limit

    logger.info(f"[get_nearby_stations] Found {count} total stations")
    return count, station_map

# Save Route Data to CSV
def save_route_data(route_features, csv_file="datasets/route_data.csv",expected_fields=None):
    logger.info(f"[save_route_data] Saving route metadata to {csv_file}")
    file_exists = os.path.isfile(csv_file)
    
    if expected_fields is None:
        expected_fields = route_features.keys()

    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=expected_fields)
        if not file_exists:
            writer.writeheader()
        writer.writerow(route_features)
    logger.info(f"[save_route_data] Route data saved to {csv_file}")


# Main Route Processing Pipeline
def run_route_pipeline(origin, destination, waypoints=None):
    logger.info("[run_route_pipeline] Running full route pipeline")
    data = get_directions(origin, destination, waypoints,avoid="") 
    
    legs = data["routes"][0]["legs"]

    origin_route = legs[0]['start_address']
    destination_route = legs[-1]['end_address']
    waypoints_route = [leg['end_address'] for leg in legs[:-1]] if len(legs) > 1 else []
    waypoints_list = "|".join(waypoints_route) if waypoints_route else ""
    encoded = data["routes"][0]["overview_polyline"]["points"]

    distance_m = sum(leg["distance"]["value"] for leg in legs)
    duration_s = sum(leg["duration"]["value"] for leg in legs)
    avg_speed = (distance_m / duration_s) * 3.6

    elevations = np.array(get_elevation(encoded))
    gain = np.sum(np.diff(elevations)[np.diff(elevations) > 0])
    max_elev = np.max(elevations)
    avg_slope = gain / len(elevations)

    distance_km = distance_m / 1000
    duration_min = duration_s / 60
    sample_points = sample_route_points(encoded, distance_km)
    station_count, station_map = get_nearby_stations(sample_points)

    route_info = {
        "origin": origin_route,
        "destination": destination_route,
        "waypoints": waypoints_list,
        "distance_km": distance_km,
        "duration_min": duration_min,
        "avg_speed_kph": avg_speed,
        "elevation_gain_m": gain,
        "max_elevation_m": max_elev,
        "avg_slope": avg_slope,                       
    }

    route_polyline = {
        "origin": origin_route,
        "destination": destination_route,
        "waypoints": waypoints_list,
        "total_stations": station_count,
        "stations_by_location": json.dumps(station_map), 
        "encoded_polyline": str(encoded),
    }
    
    route_info_fields = [
        "origin", "destination", "waypoints", "distance_km",
        "duration_min", "avg_speed_kph", "elevation_gain_m",
        "max_elevation_m", "avg_slope"
    ]
    route_polyline_fields = [
        "origin", "destination", "waypoints", "total_stations",
        "stations_by_location", "encoded_polyline"
    ]

    #save_route_data(route_info, csv_file="datasets/routes/route_info_data.csv", expected_fields=route_info_fields)
    #save_route_data(route_polyline, csv_file="datasets/routes/route_polyline_data.csv",expected_fields=route_polyline_fields)
    logger.info("[run_route_pipeline] Pipeline execution complete")
    return route_info

# Entry Point
if __name__ == "__main__":
    result = run_route_pipeline(
        origin="Almodôvar, Portugal",
        destination="Gibraleón, 21500, Huelva",
        waypoints=[]
    )
    print(result)

# Route Processing Pipeline usage example
'''
run_route_pipeline(
        origin="Girona, Spain",
        destination="Sevilla, Spain",
        waypoints=["Tarragona, Spain", "Valencia, Spain", "Madrid, Spain"]
    )
'''