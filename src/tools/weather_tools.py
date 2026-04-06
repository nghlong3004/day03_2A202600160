from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

import requests


WEATHER_API_URL = "https://api.weatherapi.com/v1/forecast.json"


def normalize_date(date_str: str) -> str:
	"""Normalize date input to YYYY-MM-DD."""
	raw = date_str.strip()
	current_year = datetime.now().year

	patterns = [
		("%d/%m", True),
		("%d-%m", True),
		("%d/%m/%Y", False),
		("%d-%m-%Y", False),
		("%Y-%m-%d", False),
	]

	for fmt, missing_year in patterns:
		try:
			dt = datetime.strptime(raw, fmt)
			if missing_year:
				dt = dt.replace(year=current_year)
			return dt.strftime("%Y-%m-%d")
		except ValueError:
			continue

	raise ValueError(f"Unsupported date format: {date_str}")


def get_weather_forecast(location: str, date: str) -> Dict[str, Any]:
	"""Get weather forecast from WeatherAPI for a specific location and date."""
	api_key = os.getenv("WEATHER_API_KEY")
	if not api_key:
		return {"success": False, "error": "Missing WEATHER_API_KEY", "results": {}}

	try:
		normalized_date = normalize_date(date)
	except ValueError as exc:
		return {"success": False, "error": str(exc), "results": {}}

	params = {
		"key": api_key,
		"q": location,
		"days": 14,
		"aqi": "no",
		"alerts": "no",
	}

	try:
		resp = requests.get(WEATHER_API_URL, params=params, timeout=20)
		resp.raise_for_status()
		data = resp.json()
	except requests.RequestException as exc:
		return {"success": False, "error": f"Weather request failed: {exc}", "results": {}}

	if "error" in data:
		return {
			"success": False,
			"error": data["error"].get("message", "Weather API error"),
			"results": {},
		}

	forecast_days = data.get("forecast", {}).get("forecastday", [])
	target = next((item for item in forecast_days if item.get("date") == normalized_date), None)

	if not target:
		available_dates = [d.get("date") for d in forecast_days if d.get("date")]
		return {
			"success": False,
			"error": "Requested date is outside current forecast window.",
			"requested_date": normalized_date,
			"available_dates": available_dates,
			"results": {},
		}

	day = target.get("day", {})
	condition = day.get("condition", {}).get("text", "Unknown")
	rain_chance = int(day.get("daily_chance_of_rain", 0) or 0)

	recommendation = "Good for camping."
	if rain_chance >= 50:
		recommendation = "High rain chance. Prepare rain gear or consider another date."
	elif float(day.get("maxtemp_c", 0) or 0) >= 34:
		recommendation = "Hot daytime weather. Bring extra water and sun protection."

	return {
		"success": True,
		"location": data.get("location", {}).get("name", location),
		"region": data.get("location", {}).get("region", ""),
		"country": data.get("location", {}).get("country", ""),
		"date": normalized_date,
		"results": {
			"condition": condition,
			"temp_min_c": day.get("mintemp_c"),
			"temp_max_c": day.get("maxtemp_c"),
			"avg_temp_c": day.get("avgtemp_c"),
			"chance_of_rain": rain_chance,
			"max_wind_kph": day.get("maxwind_kph"),
			"uv": day.get("uv"),
			"recommendation": recommendation,
		},
	}

if __name__ == "__main__":
    import json

    result = get_weather_forecast(
        location="Gia Lam, Ha Noi",
        date="06/04",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))