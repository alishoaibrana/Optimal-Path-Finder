import requests
import pandas as pd
import random
import time

API_KEY = "U9SYGlMDnFLgVG0o3eA7dXTXPE9d7Zgo"

def generate_random_coordinates():
    lat = random.uniform(-90, 90)
    lon = random.uniform(-180, 180)
    return lat, lon

# Reverse Geocoding API
def get_reverse_geocode(lat, lon):
    url = f"https://api.tomtom.com/search/2/reverseGeocode/{lat},{lon}.json?key={API_KEY}"
    res = requests.get(url).json()
    addresses = res.get('addresses', [])
    if addresses:
        addr = addresses[0]['address']
        return addr.get('street', ''), addr.get('municipality', ''), addr.get('country', ''), addr.get('postalCode', ''), addr.get('countryCode', '')
    return '', '', '', '', ''


# Traffic Incident API
def get_traffic_incident(lat, lon):
    url = f"https://api.tomtom.com/traffic/services/5/incidentDetails?key={API_KEY}&point={lat},{lon}&radius=5000&fields={{incidents{{type,geometry{{type,coordinates}},properties}}}}"
    res = requests.get(url).json()
    incidents = res.get('incidents', [])
    return len(incidents)

# Traffic Flow (Average Speed, Traffic Yes/No)
def get_traffic_flow(lat, lon):
    url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?point={lat},{lon}&key={API_KEY}"
    res = requests.get(url).json()
    try:
        flow = res['flowSegmentData']
        return flow['currentSpeed'], flow['freeFlowSpeed'], 'Yes' if flow['currentSpeed'] < flow['freeFlowSpeed'] else 'No'
    except:
        return None, None, 'Unknown'

# SnapToRoad API
def snap_to_road(lat, lon):
    url = f"https://api.tomtom.com/map/match/1/snapToRoad?key={API_KEY}&point={lat},{lon}"
    response = requests.get(url)
    if response.status_code == 200:
        res = response.json()
        try:
            return res['matchedPoints'][0]['latitude'], res['matchedPoints'][0]['longitude']
        except:
            return None, None
    else:
        print(f"SnapToRoad API error {response.status_code} at {lat},{lon}")
        return None, None

# Weather API (assuming external API as TomTom doesn’t offer it directly — e.g., OpenWeather)
def get_weather(lat, lon):
    # Placeholder or use OpenWeatherMap API
    return 'Sunny', 32.5

# Placeholder for Matrix Routing API call
def get_matrix_routing_data(orig_lat, orig_lon, dest_lat, dest_lon):
    url = f"https://api.tomtom.com/routing/matrix/2?key={API_KEY}&routeType=fastest"
    # Example body — normally you'd POST this
    return random.randint(1, 30)

# Similarly you can mock / call
def get_ev_routing_data():
    return random.randint(1, 10)

def get_geofence_status():
    return random.choice(['Inside', 'Outside'])

def get_notification_status():
    return random.choice(['Sent', 'Not Sent'])

def get_location_history():
    return random.randint(0, 20)

# Collect Data
data = []

for i in range(1000):
    lat, lon = generate_random_coordinates()
    street, city, country, postal, country_code = get_reverse_geocode(lat, lon)
    incidents = get_traffic_incident(lat, lon)
    current_speed, free_flow_speed, traffic_status = get_traffic_flow(lat, lon)
    snap_lat, snap_lon = snap_to_road(lat, lon)
    weather_condition, temperature = get_weather(lat, lon)
    matrix_route_time = get_matrix_routing_data(lat, lon, lat+0.1, lon+0.1)
    ev_route_estimate = get_ev_routing_data()
    geofence_status = get_geofence_status()
    notification_status = get_notification_status()
    location_history = get_location_history()

    data.append({
        'latitude': lat,
        'longitude': lon,
        'street': street,
        'city': city,
        'country': country,
        'postalCode': postal,
        'countryCode': country_code,
        'incidents': incidents,
        'currentSpeed': current_speed,
        'freeFlowSpeed': free_flow_speed,
        'traffic': traffic_status,
        'snapLat': snap_lat,
        'snapLon': snap_lon,
        'weather': weather_condition,
        'temperature': temperature,
        'matrixRouteTime': matrix_route_time,
        'evRouteEstimate': ev_route_estimate,
        'geofenceStatus': geofence_status,
        'notificationStatus': notification_status,
        'locationHistoryCount': location_history
    })

    print(f"Collected {i+1}/1000 records")
    time.sleep(0.2)

# Save to CSV
df = pd.DataFrame(data)
df.to_csv("comprehensive_tomtom_dataset.csv", index=False)
print("Dataset saved as 'comprehensive_tomtom_dataset.csv'.")

