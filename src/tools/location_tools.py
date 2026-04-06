from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List, Optional

import requests


GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"


def calculate_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great distance in kilometers between two points on the Earth."""
    earth_radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c


def get_geolocation(location: str, api_key: str) -> Optional[Dict[str, float]]:
    """Convert a location string into latitude and longitude using Google Geocoding API."""
    params = {"address": location, "key": api_key}
    resp = requests.get(GEOCODE_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    status = data.get("status")
    if status != "OK" or not data.get("results"):
        error_message = data.get("error_message", "No geocoding results")
        raise ValueError(f"Geocoding API error ({status}): {error_message}")

    point = data["results"][0]["geometry"]["location"]
    return {"lat": point["lat"], "lon": point["lng"]}


def is_family_friendly(place: Dict[str, Any], amenities: List[str]) -> bool:
    """Determine if a place is family-friendly based on its types, rating, and user reviews."""
    req = {a.strip().lower() for a in amenities}
    if "family_friendly" not in req:
        return True

    types = [t.lower() for t in place.get("types", [])]
    rating = float(place.get("rating", 0) or 0)
    review_count = int(place.get("userRatingCount", 0) or 0)

    has_family_type = any(t in types for t in ["park", "campground", "tourist_attraction", "rv_park"])
    has_quality_signal = rating >= 4.0 and review_count >= 20

    return has_family_type or has_quality_signal


def search_camp_site(
    location: str,
    radius_km: float = 15,
    capacity: int = 1,
    amenities: Optional[List[str]] = None,
) -> Dict[str, Any]:
    api_key = os.getenv("PLACES_API_KEY")
    if not api_key:
        return {"success": False, "error": "Missing PLACES_API_KEY", "results": []}

    amenities = amenities or []

    try:
        center = get_geolocation(location, api_key)
    except ValueError as exc:
        return {"success": False, "error": str(exc), "results": []}
    except requests.RequestException as exc:
        return {"success": False, "error": f"Geocoding failed: {exc}", "results": []}

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": ",".join(
            [
                "places.displayName",
                "places.formattedAddress",
                "places.location",
                "places.types",
                "places.rating",
                "places.userRatingCount",
                "places.googleMapsUri",
            ]
        ),
    }

    body = {
        "includedTypes": ["campground", "park", "rv_park", "tourist_attraction"],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": center["lat"], "longitude": center["lon"]},
                "radius": float(radius_km) * 1000.0,
            }
        },
        "rankPreference": "DISTANCE",
    }

    try:
        resp = requests.post(PLACES_NEARBY_URL, headers=headers, json=body, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return {"success": False, "error": f"Places search failed: {exc}", "results": []}

    results: List[Dict[str, Any]] = []

    for place in data.get("places", []):
        point = place.get("location", {})
        lat = point.get("latitude")
        lon = point.get("longitude")
        if lat is None or lon is None:
            continue

        distance_km = calculate_haversine(center["lat"], center["lon"], lat, lon)
        if distance_km > radius_km:
            continue

        if not is_family_friendly(place, amenities):
            continue

        # Keep only places with real rating data.
        if place.get("rating") is None:
            continue
        if int(place.get("userRatingCount", 0) or 0) <= 0:
            continue

        types = [t.lower() for t in place.get("types", [])]
        estimated_capacity = 4
        if "park" in types:
            estimated_capacity = 12
        elif "campground" in types:
            estimated_capacity = 8

        if estimated_capacity < capacity:
            continue

        results.append(
            {
                "name": place.get("displayName", {}).get("text", "Unknown"),
                "address": place.get("formattedAddress", ""),
                "distance_km": round(distance_km, 2),
                "rating": float(place.get("rating", 0) or 0),
                "user_rating_count": place.get("userRatingCount", 0),
                "estimated_capacity": estimated_capacity,
                "types": place.get("types", []),
            }
        )

    results.sort(key=lambda x: x["distance_km"])
    top_results = results[:3]

    return {
        "success": True,
        "location": location,
        "radius_km": radius_km,
        "count": len(top_results),
        "results": top_results,
    }


if __name__ == "__main__":
    result = search_camp_site(
        location="Gia Lam, Ha Noi",
        radius_km=15,
        capacity=4,
        amenities=["family_friendly"],
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
