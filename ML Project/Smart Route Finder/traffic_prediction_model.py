import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import numpy as np
import joblib
from datetime import datetime, timedelta
import pandas as pd
from urllib.parse import urlencode

# Load trained model and preprocessing tools
model_data = joblib.load('traffic_prediction_model.pkl')
model = model_data['model']
scaler = model_data['scaler']
le_weather = model_data['le_weather']
le_road = model_data['le_road']
le_traffic = model_data['le_traffic']
feature_names = model_data['feature_names']

# -----------------------------
# API Keys
TOMTOM_API_KEY = 'vIQFHwtFspqrlUltQRMkXRZx34MGGHFY'
OPENWEATHER_API_KEY = 'c41ad81235ca0a45594610502b05b89f'

# -----------------------------
# Sidebar
st.sidebar.title("📂 Navigation")
theme = st.sidebar.radio("🎨 Theme", ["Light", "Dark"])
st.sidebar.button("🔁 Route History")
st.sidebar.button("⚙ Settings")
st.sidebar.markdown("---")
st.sidebar.info("ℹ Powered by TomTom, OpenWeather & ML")

# -----------------------------
# Heading
st.markdown("<h1 style='text-align: center;'>🚗 Smart Route Dashboard</h1>", unsafe_allow_html=True)

# -----------------------------
# Input section
st.subheader("🔍 Enter Route Details")
col_pickup, col_dropoff = st.columns(2)
with col_pickup:
    pickup = st.text_input("Pickup Location", placeholder="e.g., New York City", key="pickup")
with col_dropoff:
    dropoff = st.text_input("Drop-off Location", placeholder="e.g., Times Square", key="dropoff")

if st.button("🚀 Find Route"):
    st.session_state["find_route"] = True

# -----------------------------
# Helper Functions
def get_coordinates(location):
    url = f"https://api.tomtom.com/search/2/geocode/{location}.json?key={TOMTOM_API_KEY}"
    res = requests.get(url).json()
    try:
        lat = res['results'][0]['position']['lat']
        lon = res['results'][0]['position']['lon']
        return lat, lon
    except:
        return None, None

def get_traffic_conditions(lat, lon):
    url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json?point={lat},{lon}&key={TOMTOM_API_KEY}"
    res = requests.get(url).json()
    try:
        speed = res['flowSegmentData']['currentSpeed']
        free_flow_speed = res['flowSegmentData']['freeFlowSpeed']
        congestion = "Heavy" if speed < 0.5 * free_flow_speed else "Moderate" if speed < 0.8 * free_flow_speed else "Light"
        return congestion
    except:
        return "Unavailable"

def get_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    res = requests.get(url).json()
    try:
        weather = res['weather'][0]['description']
        temp = res['main']['temp']
        return f"{weather.capitalize()}, {temp}°C"
    except:
        return "Unavailable"

def get_incidents(lat, lon):
    url = f"https://api.tomtom.com/traffic/services/5/incidentDetails?key={TOMTOM_API_KEY}&bbox={lat-0.1},{lon-0.1},{lat+0.1},{lon+0.1}"
    res = requests.get(url).json()
    try:
        incidents = res.get("incidents", [])
        return f"{len(incidents)} incident(s) nearby" if incidents else "No incidents"
    except:
        return "Unavailable"

def normalize_weather(description):
    description = description.lower()
    if 'snow' in description:
        return 'snow'
    elif 'rain' in description or 'drizzle' in description:
        return 'rain'
    elif 'fog' in description or 'mist' in description or 'haze' in description:
        return 'fog'
    elif 'clear' in description:
        return 'clear'
    elif 'cloud' in description:
        return 'clear'
    else:
        return 'clear'

def predict_traffic(pickup_lat, pickup_lon, drop_lat, drop_lon):
    numerical_features = [
        'free_flow_travel_time_seconds',
        'travel_time_seconds',
        'distance_meters',
        'hour'
    ]

    route_url = f"https://api.tomtom.com/routing/1/calculateRoute/{pickup_lat},{pickup_lon}:{drop_lat},{drop_lon}/json?key={TOMTOM_API_KEY}&travelMode=car"
    route_res = requests.get(route_url).json()

    try:
        leg = route_res['routes'][0]['legs'][0]
        travel_time_sec = leg['summary']['travelTimeInSeconds']
        free_flow_time_sec = leg['summary']['trafficDelayInSeconds'] + leg['summary']['travelTimeInSeconds']
        distance_meters = leg['summary']['lengthInMeters']
    except:
        return "Prediction unavailable (TomTom failed)"

    weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={pickup_lat}&lon={pickup_lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    weather_res = requests.get(weather_url).json()
    try:
        raw_weather = weather_res['weather'][0]['description']
        weather_condition = normalize_weather(raw_weather)
    except:
        return "Prediction unavailable (Weather failed)"

    road_type = 'highway'
    hour = datetime.now().hour

    try:
        weather_enc = le_weather.transform([weather_condition])[0]
        road_enc = le_road.transform([road_type])[0]
    except:
        return "Encoding error"

    input_data = pd.DataFrame([{ 
        'free_flow_travel_time_seconds': free_flow_time_sec,
        'travel_time_seconds': travel_time_sec,
        'distance_meters': distance_meters,
        'weather_condition': weather_enc,
        'road_type': road_enc,
        'hour': hour
    }])

    input_data[numerical_features] = scaler.transform(input_data[numerical_features])

    pred_encoded = model.predict(input_data)[0]
    pred_label = le_traffic.inverse_transform([pred_encoded])[0]

    return pred_label

def get_route(pickup_lat, pickup_lon, drop_lat, drop_lon):
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{pickup_lat},{pickup_lon}:{drop_lat},{drop_lon}/json?key={TOMTOM_API_KEY}&travelMode=car&maxAlternatives=2"
    res = requests.get(url).json()
    try:
        return [
            [(p["latitude"], p["longitude"]) for p in route["legs"][0]["points"]]
            for route in res["routes"]
        ]
    except:
        return []

# -----------------------------
# Results
if st.session_state.get("find_route", False):
    with st.spinner("Fetching route and data..."):
        pickup_lat, pickup_lon = get_coordinates(st.session_state["pickup"])
        drop_lat, drop_lon = get_coordinates(st.session_state["dropoff"])

        if pickup_lat is None or drop_lat is None:
            st.error("❌ Invalid location(s). Please check your input.")
        else:
            st.success(f"📍 Route from {pickup} ➡ {dropoff}")

            share_url = f"?{urlencode({'pickup': pickup, 'dropoff': dropoff})}"

            tabs = st.tabs(["📊 Info", "🗺 Map", "⚙ Advanced"])
            with tabs[0]:
                col1, col2 = st.columns(2)
                with col1:
                    st.write("🚦 Traffic (Pickup):", get_traffic_conditions(pickup_lat, pickup_lon))
                    st.write("☁ Weather (Pickup):", get_weather(pickup_lat, pickup_lon))
                    st.write("☁ Weather (Drop-Off):", get_weather(drop_lat, drop_lon))
                with col2:
                    st.write("🛠 Incidents (Pickup):", get_incidents(pickup_lat, pickup_lon))
                    st.write("🤖 Traffic Exists (ML):", predict_traffic(pickup_lat, pickup_lon, drop_lat, drop_lon))

            with tabs[1]:
                route_options = get_route(pickup_lat, pickup_lon, drop_lat, drop_lon)
                if route_options:
                    tiles = "Stamen Toner" if theme == "Dark" else "OpenStreetMap"
                    route_map = folium.Map(location=[pickup_lat, pickup_lon], zoom_start=12, tiles=tiles)
                    folium.Marker([pickup_lat, pickup_lon], tooltip="Pickup", icon=folium.Icon(color="green")).add_to(route_map)
                    folium.Marker([drop_lat, drop_lon], tooltip="Drop-off", icon=folium.Icon(color="red")).add_to(route_map)
                    for i, points in enumerate(route_options):
                        folium.PolyLine(points, color=["blue", "orange", "purple"][i % 3], weight=5, tooltip=f"Route {i+1}").add_to(route_map)
                    st_folium(route_map, width=700, height=500)

                    if st.button("📍 Drop Custom Pin"):
                        st.info("Click on the map to add pins (not implemented yet).")

                    st.markdown("📸 **Live Traffic Snapshot:** [TomTom Traffic](https://www.tomtom.com/en_gb/traffic-index/)")
                else:
                    st.warning("Unable to fetch route.")

            with tabs[2]:
                st.markdown(f"🔗 **Share this route link:** `{share_url}`")
                schedule_time = st.time_input("🕒 Schedule this trip for:", value=datetime.now().time())
                if st.button("📅 Schedule Trip"):
                    st.success(f"Trip scheduled at {schedule_time} (functionality stub).")

                if st.button("⭐ Save to Favorites"):
                    st.success("Route saved (session-based).")

                st.markdown("📈 **Traffic History Visualization (stub)**")
                st.line_chart(pd.Series(np.random.randint(30, 90, 12), name="Avg Speed (km/h)"))

                st.markdown("🌤 **Weather Forecast Panel (stub)**")
                st.write("- 1hr: Clear, 23°C")
                st.write("- 2hr: Cloudy, 22°C")
                st.write("- 3hr: Rain, 20°C")

            if st.button("🔄 Reset"):
                st.session_state["find_route"] = False

# -----------------------------
# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; font-size: 0.9em;'>© 2025 Route Dashboard | Built with ❤ using Streamlit, TomTom & OpenWeather APIs</p>", unsafe_allow_html=True)
