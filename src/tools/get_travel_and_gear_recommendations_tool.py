import math
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
import requests

from src.tools.location_tools import search_camp_site
from src.tools.weather_tools import get_weather_forecast

WEATHER_API_URL = "https://api.weatherapi.com/v1/forecast.json"
PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
GEOCODING_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

def _append_unique(bucket: List[str], items: List[str]) -> None:
    for item in items:
        if item not in bucket:
            bucket.append(item)

def _build_gear_recommendations(
    weather: Dict[str, Any],
    group_type: str,
    capacity: int,
    amenities: List[str],
) -> Dict[str, List[str]]:
    gear = {
        "shelter": [],
        "clothing": [],
        "food_and_water": [],
        "safety": [],
        "comfort": [],
    }

    max_temp = float(weather.get("temp_max_c", 0) or 0)
    min_temp = float(weather.get("temp_min_c", 0) or 0)
    rain_chance = int(weather.get("chance_of_rain", 0) or 0)
    max_wind = float(weather.get("max_wind_kph", 0) or 0)
    uv = float(weather.get("uv", 0) or 0)
    _append_unique(gear["shelter"], ["Tent", "Ground sheet", "Sleeping bag"])
    _append_unique(gear["food_and_water"], ["Water bottles", "Snacks", "Trash bags"])
    _append_unique(gear["safety"], ["First-aid kit", "Flashlight", "Phone power bank"])
    if rain_chance >= 50:
        _append_unique(
            gear["shelter"],
            ["Rain fly", "Extra tent stakes", "Waterproof tarp"],
        )
        _append_unique(
            gear["clothing"],
            ["Rain jacket", "Quick-dry clothes", "Waterproof shoes or sandals"],
        )
        if max_temp >= 34:
            _append_unique(
                gear["clothing"],
                ["Breathable clothes", "Wide-brim hat", "Sunglasses"],
            )
            _append_unique(
                gear["food_and_water"],
                ["Extra drinking water", "Electrolyte packets"],
            )
            _append_unique(gear["safety"], ["Sunscreen"])
        if min_temp <= 18:
            _append_unique(
                gear["clothing"],
                ["Warm jacket", "Long pants", "Extra socks"],
            )
            _append_unique(gear["comfort"], ["Blanket or fleece layer"])
        if max_wind >= 25:
            _append_unique(
                gear["shelter"],
                ["Wind-resistant tent lines"],
            )
            _append_unique(
                gear["clothing"],
                ["Windproof outer layer"],
            )
        if uv >= 7:
            _append_unique(gear["safety"], ["High-SPF sunscreen", "Lip balm with SPF"])
        if capacity >= 4:
            _append_unique(
                gear["shelter"],
                ["Large family tent", "Extra camping chairs"],
            )
            _append_unique(gear["food_and_water"], ["Portable cooler"])
        normalized_group = group_type.strip().lower()
        if "family" in normalized_group:
            _append_unique(
                gear["comfort"],
                ["Picnic mat", "Wet wipes", "Kids change of clothes"],
            )
        elif "couple" in normalized_group:
            _append_unique(
                gear["comfort"],
                ["Compact picnic setup", "Portable lantern"],
            )
        elif "friends" in normalized_group or "group" in normalized_group:
            _append_unique(
                gear["comfort"],
                ["Extra chairs", "Portable speaker", "Shared cooking set"],
            )
        normalized_amenities = {item.strip().lower() for item in amenities if item.strip()}
        if "toilet" not in normalized_amenities and "restroom" not in normalized_amenities:
            _append_unique(gear["comfort"], ["Tissue paper", "Hand sanitizer"])
        if "water" not in normalized_amenities:
            _append_unique(gear["food_and_water"], ["Extra clean water container"])
        return gear
    
def _build_travel_notes(
    weather_result: Dict[str, Any],
    camp_result: Dict[str, Any],
    radius_km: float,
) -> List[str]:
    notes: List[str] = []
    weather = weather_result.get("results", {}) if weather_result.get("success") else {}
    camps = camp_result.get("results", []) if camp_result.get("success") else []
    if weather:
        notes.append(weather.get("recommendation", ""))
        rain_chance = int(weather.get("chance_of_rain", 0) or 0)
        if rain_chance >= 70:
            notes.append("Rain probability is high, so plan a backup indoor option.")
        if float(weather.get("max_wind_kph", 0) or 0) >= 30:
            notes.append("Wind conditions may make tent setup less comfortable.")
    elif weather_result.get("error"):
        notes.append(f"Weather forecast unavailable: {weather_result['error']}")
    if camps:
        best_site = camps[0]
        notes.append(
            f"Nearest suitable campsite is {best_site['name']} "
            f"({best_site['distance_km']} km away, rating {best_site['rating']})."
        )
        if best_site.get("distance_km", 0) > radius_km * 0.7:
            notes.append("Most good campsites are near the edge of your radius, so consider widening the search.")
    elif camp_result.get("error"):
        notes.append(f"Camp site search unavailable: {camp_result['error']}")
    else:
        notes.append("No campsite matched the current filters. Try increasing radius or relaxing amenities.")
    return [note for note in notes if note]


def get_travel_and_gear_recommendations(
    location: str,
    date: str,
    radius_km: float = 15,
    capacity: int = 1,
    amenities: Optional[List[str]] = None,
    group_type: str = "general",
) -> Dict[str, Any]:
    """
    Combine campsite search and weather forecast into one structured recommendation.
    This tool does not fabricate live data: it relies on the outputs of
    search_camp_site(...) and get_weather_forecast(...).
    """
    amenities = amenities or []

    camp_result = search_camp_site(
        location=location,
        radius_km=radius_km,
        capacity=capacity,
        amenities=amenities,
    )
    weather_result = get_weather_forecast(location=location, date=date)

    errors: List[str] = []
    if not camp_result.get("success"):
        errors.append(camp_result.get("error", "Camp site search failed."))
    if not weather_result.get("success"):
        errors.append(weather_result.get("error", "Weather forecast failed."))

    weather_payload = weather_result.get("results", {}) if weather_result.get("success") else {}
    camp_sites = camp_result.get("results", []) if camp_result.get("success") else []

    gear_recommendations = _build_gear_recommendations(
        weather=weather_payload,
        group_type=group_type,
        capacity=capacity,
        amenities=amenities,
    )
    travel_notes = _build_travel_notes(
        weather_result=weather_result,
        camp_result=camp_result,
        radius_km=radius_km,
    )

    best_site = camp_sites[0] if camp_sites else None

    return {
        "success": len(errors) == 0,
        "partial": 0 < len(errors) < 2,
        "errors": errors,
        "location": location,
        "date": weather_result.get("date", date),
        "group_type": group_type,
        "capacity": capacity,
        "requested_amenities": amenities,
        "weather_forecast": weather_payload,
        "camp_site_search": {
            "radius_km": radius_km,
            "count": camp_result.get("count", 0),
            "best_match": best_site,
            "alternatives": camp_sites[1:] if len(camp_sites) > 1 else [],
        },
        "travel_notes": travel_notes,
        "gear_recommendations": gear_recommendations,
    }


def finish(result: Dict[str, Any]) -> str:
    """Format the recommendation result into a user-facing answer."""
    if not result:
        return "No recommendation data is available."

    if not result.get("success"):
        errors = result.get("errors", [])
        if errors:
            error_text = " \n".join(f"- {error}" for error in errors)
            if result.get("partial"):
                return (
                    "I found partial information, but there were issues:\n"
                    f"{error_text}"
                )
            return f"Unable to provide a full recommendation due to the following errors:\n{error_text}"
        return "Unable to provide a recommendation."

    parts: List[str] = []
    location = result.get("location", "the requested location")
    date = result.get("date", "the requested date")
    parts.append(f"Travel and gear recommendations for {location} on {date}:")

    weather = result.get("weather_forecast", {})
    if weather:
        summary = weather.get("condition", weather.get("description")) or "Weather details unavailable"
        temp_max = weather.get("temp_max_c")
        temp_min = weather.get("temp_min_c")
        parts.append(f"- Weather: {summary}")
        if temp_max is not None or temp_min is not None:
            temps = []
            if temp_min is not None:
                temps.append(f"low {temp_min}°C")
            if temp_max is not None:
                temps.append(f"high {temp_max}°C")
            parts.append(f"  Expected temperatures: {', '.join(temps)}.")

    best_site = result.get("camp_site_search", {}).get("best_match")
    if best_site:
        name = best_site.get("name", "a campsite")
        distance = best_site.get("distance_km")
        rating = best_site.get("rating")
        site_line = f"- Best campsite: {name}"
        if distance is not None:
            site_line += f" ({distance} km away)"
        if rating is not None:
            site_line += f", rating {rating}"
        parts.append(site_line + ".")

    notes = result.get("travel_notes", [])
    if notes:
        parts.append("- Travel notes:")
        for note in notes:
            parts.append(f"  • {note}")

    gear = result.get("gear_recommendations", {})
    if gear:
        parts.append("- Recommended gear:")
        for category, items in gear.items():
            if items:
                parts.append(f"  {category.replace('_', ' ').title()}: {', '.join(items)}")

    return "\n".join(parts)
