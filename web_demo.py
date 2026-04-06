import json
import os
import traceback
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from src.agent.agent import ReActAgent
from src.agent.chatbot import BaselineChatbot
from src.core.openai_provider import OpenAIProvider
from src.core.openrouter_provider import OpenRouterProvider
from src.tools.get_travel_and_gear_recommendations_tool import get_travel_and_gear_recommendations
from src.tools.location_tools import search_camp_site
from src.tools.weather_tools import get_weather_forecast

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

TOOL_SEARCH_CAMP = {
    "name": "search_camp_site",
    "description": (
        "Tìm địa điểm cắm trại gần khu vực chỉ định. "
        'Action Input phải là JSON dạng {"location":"Gia Lâm, Hà Nội","radius_km":20,"capacity":4,"amenities":["family_friendly"]}.'
    ),
    "func": search_camp_site,
}

TOOL_GET_WEATHER = {
    "name": "get_weather_forecast",
    "description": (
        "Lấy dự báo thời tiết cho địa điểm và ngày cụ thể. "
        'Action Input phải là JSON dạng {"location":"Gia Lâm, Hà Nội","date":"2026-04-10"}.'
    ),
    "func": get_weather_forecast,
}

TOOL_GET_TRAVEL_AND_GEAR = {
    "name": "get_travel_and_gear_recommendations",
    "description": (
        "Tổng hợp gợi ý địa điểm, thời tiết, di chuyển và đồ đạc cần mang cho chuyến cắm trại gia đình."
    ),
    "func": get_travel_and_gear_recommendations,
}

TOOLS = [TOOL_SEARCH_CAMP, TOOL_GET_WEATHER, TOOL_GET_TRAVEL_AND_GEAR]


def _resolve_provider():
    provider_name = os.getenv("DEFAULT_PROVIDER", "gemini").strip().lower()
    model_name = os.getenv("MODEL_NAME", "").strip() or os.getenv("DEFAULT_MODEL", "").strip()

    if provider_name == "openai":
        return OpenAIProvider(
            model_name=model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    if provider_name == "deepseek":
        return OpenAIProvider(
            model_name=model_name or os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            provider_name="deepseek",
        )
    if provider_name == "openrouter":
        return OpenRouterProvider(
            model_name=model_name or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    from src.core.gemini_provider import GeminiProvider

    return GeminiProvider(
        model_name=model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        api_key=os.getenv("GEMINI_API_KEY"),
    )


def _build_services():
    llm = _resolve_provider()
    return {
        "baseline": BaselineChatbot(llm),
        "agent": ReActAgent(llm=llm, tools=TOOLS),
    }


SERVICES = _build_services()


def build_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    usage = result.get("usage", {})
    provider = result.get("provider", "unknown")
    model = result.get("model", "unknown")
    return {
        "provider": provider,
        "model": model,
        "latency_ms": result.get("latency_ms", 0),
        "tool_calls": len(result.get("tool_calls", [])),
        "steps": result.get("steps", 1),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
    }


class DemoRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: Optional[str] = None, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        try:
            payload = self._read_json_body()
            question = str(payload.get("question", "")).strip()
            mode = str(payload.get("mode", "baseline")).strip().lower()

            if not question:
                self._write_json({"error": "Thiếu nội dung câu hỏi."}, status=HTTPStatus.BAD_REQUEST)
                return

            if mode not in SERVICES:
                self._write_json({"error": "Chế độ không hợp lệ."}, status=HTTPStatus.BAD_REQUEST)
                return

            service = SERVICES[mode]
            result = service.run_with_metadata(question)
            response = {
                "mode": mode,
                "answer": result.get("answer", ""),
                "trace": result.get("trace", []),
                "tool_calls": result.get("tool_calls", []),
                "metrics": build_metrics(result),
            }
            self._write_json(response)
        except Exception as exc:
            traceback.print_exc()
            self._write_json(
                {
                    "error": "Không thể xử lý yêu cầu.",
                    "detail": str(exc),
                },
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def end_headers(self):
        self._send_cors_headers()
        super().end_headers()

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _read_json_body(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        return json.loads(raw_body.decode("utf-8"))

    def _write_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str = "127.0.0.1", port: int = 8000):
    handler = partial(DemoRequestHandler, directory=str(FRONTEND_DIR))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Demo server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
