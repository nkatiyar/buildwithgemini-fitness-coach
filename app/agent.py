# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.cloud import firestore
from google.genai import types


MODEL = "gemini-3.6-flash"
PROJECT_ID = "qwiklabs-gcp-04-f27982afaad3"

# Initialize Firestore Client with hardcoded project ID
db = firestore.Client(project=PROJECT_ID)


def list_workouts(muscle_group: Optional[str] = None, max_duration_minutes: Optional[int] = None) -> List[Dict[str, Any]]:
    """List available workouts from the workout catalog with optional filtering.

    Args:
        muscle_group: Optional muscle group or focus area to filter by (e.g. 'Core', 'Full Body', 'Legs', 'Upper Body').
        max_duration_minutes: Optional maximum duration in minutes to filter workouts.

    Returns:
        A list of workout objects from the catalog.
    """
    workouts_ref = db.collection("workouts")
    docs = workouts_ref.stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        if muscle_group:
            target_muscles = [m.lower() for m in data.get("target_muscles", [])]
            if not any(muscle_group.lower() in m for m in target_muscles):
                continue

        if max_duration_minutes is not None:
            if data.get("duration_minutes", 0) > max_duration_minutes:
                continue

        results.append(data)

    return results


def get_workout_details(workout_id: str) -> Dict[str, Any]:
    """Retrieve full details of a specific workout from the catalog.

    Args:
        workout_id: The unique identifier of the workout (e.g. 'hiit-full-body', 'core-mobility-flow').

    Returns:
        A dictionary containing the workout details or an error message if not found.
    """
    doc = db.collection("workouts").document(workout_id).get()
    if not doc.exists:
        return {"error": f"Workout '{workout_id}' not found in catalog."}
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def log_completed_workout(
    workout_title: str,
    duration_minutes: int,
    calories_burned: Optional[int] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Log a completed workout session to the user's workout log.

    Args:
        workout_title: The name or title of the workout completed.
        duration_minutes: Number of minutes spent working out.
        calories_burned: Optional estimated calories burned during the workout.
        notes: Optional user notes, thoughts, or difficulty reflections.

    Returns:
        A confirmation dictionary including the log ID and timestamp.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    log_entry = {
        "workout_title": workout_title,
        "duration_minutes": duration_minutes,
        "calories_burned": calories_burned or 0,
        "notes": notes or "",
        "timestamp": now.isoformat(),
        "created_at": firestore.SERVER_TIMESTAMP,
    }

    doc_ref = db.collection("workout_logs").document()
    doc_ref.set(log_entry)

    return {
        "status": "success",
        "log_id": doc_ref.id,
        "message": f"Logged workout '{workout_title}' ({duration_minutes} mins). Great job!",
        "timestamp": log_entry["timestamp"],
    }


def get_recent_workout_logs(limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve recently logged workout sessions for the user.

    Args:
        limit: Maximum number of recent logs to fetch (default: 5).

    Returns:
        A list of recent workout log entries ordered by timestamp.
    """
    logs_ref = db.collection("workout_logs").order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
    docs = logs_ref.stream()

    logs = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        if "created_at" in item and item["created_at"]:
            item["created_at"] = str(item["created_at"])
        logs.append(item)
    return logs


def calculate_heart_rate_zones(age: int, resting_hr: Optional[int] = None) -> Dict[str, Any]:
    """Calculate customized heart rate training zones for exercise.

    Uses the Karvonen formula if resting heart rate is provided, or the Tanaka formula (208 - 0.7 * age).

    Args:
        age: The user's age in years.
        resting_hr: Optional resting heart rate in beats per minute (bpm).

    Returns:
        A dictionary with estimated max heart rate and target BPM ranges for 5 training zones:
        Zone 1 (Warm up/Recovery 50-60%), Zone 2 (Fat Burn/Base 60-70%), Zone 3 (Aerobic/Cardio 70-80%),
        Zone 4 (Anaerobic/Threshold 80-90%), and Zone 5 (Neuromuscular/Peak 90-100%).
    """
    max_hr = round(208 - (0.7 * age))

    if resting_hr is not None and 35 <= resting_hr <= 120:
        hr_reserve = max_hr - resting_hr
        calc_bpm = lambda pct: round(resting_hr + (hr_reserve * pct))
        method = "Karvonen (Heart Rate Reserve)"
    else:
        calc_bpm = lambda pct: round(max_hr * pct)
        method = "Tanaka Standard Formula"

    zones = {
        "zone_1_warmup": {
            "name": "Zone 1: Active Recovery & Warm-up (50-60%)",
            "range_bpm": f"{calc_bpm(0.50)} - {calc_bpm(0.60)} bpm",
            "benefit": "Warm up, active recovery, cool down.",
        },
        "zone_2_fat_burn": {
            "name": "Zone 2: Aerobic Base & Fat Burn (60-70%)",
            "range_bpm": f"{calc_bpm(0.60)} - {calc_bpm(0.70)} bpm",
            "benefit": "Builds endurance, optimizes lipid metabolism, conversational pace.",
        },
        "zone_3_aerobic": {
            "name": "Zone 3: Tempo & Cardio (70-80%)",
            "range_bpm": f"{calc_bpm(0.70)} - {calc_bpm(0.80)} bpm",
            "benefit": "Improves cardiovascular capacity and aerobic fitness.",
        },
        "zone_4_threshold": {
            "name": "Zone 4: Anaerobic Threshold (80-90%)",
            "range_bpm": f"{calc_bpm(0.80)} - {calc_bpm(0.90)} bpm",
            "benefit": "Increases lactate threshold and high-speed endurance.",
        },
        "zone_5_peak": {
            "name": "Zone 5: Maximum Effort / Sprint (90-100%)",
            "range_bpm": f"{calc_bpm(0.90)} - {max_hr} bpm",
            "benefit": "Peak interval sprint power and neuromuscular velocity.",
        },
    }

    return {
        "user_age": age,
        "resting_heart_rate": resting_hr,
        "estimated_max_hr": max_hr,
        "calculation_method": method,
        "zones": zones,
    }


import json
import os
import urllib.request


def search_public_exercises(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search an open public database (wger REST API) for exercise names, equipment, and target muscles.

    Args:
        query: The search keyword (e.g. 'press', 'squat', 'curl', 'dumbbell', 'kettlebell').
        limit: Maximum number of exercises to return (default: 5).

    Returns:
        A list of matching exercises with name, category, equipment, and targeted muscles.
    """
    api_key = os.environ.get("WGER_API_KEY")
    url = f"https://wger.de/api/v2/exerciseinfo/?limit=60"
    headers = {"User-Agent": "FitnessCoachApp/1.0"}
    if api_key:
        headers["Authorization"] = f"Token {api_key}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))

        results = []
        q_lower = query.strip().lower()

        for item in payload.get("results", []):
            muscles = [m.get("name") for m in item.get("muscles", []) if m.get("name")]
            equipment = [eq.get("name") for eq in item.get("equipment", []) if eq.get("name")]
            category = item.get("category", {}).get("name", "")

            # Look through English translations
            for trans in item.get("translations", []):
                if trans.get("language") == 2:  # English
                    name = trans.get("name", "")
                    description = trans.get("description", "").replace("<p>", "").replace("</p>", "").strip()
                    searchable_text = f"{name} {category} {' '.join(equipment)} {' '.join(muscles)}".lower()

                    if q_lower in searchable_text:
                        results.append({
                            "name": name,
                            "category": category,
                            "equipment": equipment,
                            "target_muscles": muscles,
                            "description": description[:180] + ("..." if len(description) > 180 else ""),
                        })
                        break

            if len(results) >= limit:
                break

        return results if results else [{"message": f"No public exercises matched '{query}' in the wger catalog."}]

    except Exception as e:
        return [{"error": f"Failed to fetch public exercises: {str(e)}"}]


import urllib.parse


def geocode_address(address: str) -> Dict[str, Any]:
    """Convert a street address or location name into latitude/longitude coordinates.

    Tries the Geocoding API endpoint first, and falls back to Places API (New) Text Search.

    Args:
        address: The address or place description (e.g. '1600 Amphitheatre Parkway, Mountain View, CA').

    Returns:
        A dictionary with formatted address, latitude, and longitude.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    # Attempt Geocoding REST API endpoint
    try:
        geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
        req = urllib.request.Request(geo_url)
        with urllib.request.urlopen(req, timeout=6) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("status") == "OK" and data.get("results"):
                res = data["results"][0]
                return {
                    "formatted_address": res.get("formatted_address"),
                    "location": res.get("geometry", {}).get("location"),
                }
    except Exception:
        pass

    # Fallback using Places API (New) searchText
    try:
        places_text_url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
        }
        body = json.dumps({"textQuery": address}).encode("utf-8")
        req = urllib.request.Request(places_text_url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("places"):
                p = data["places"][0]
                return {
                    "formatted_address": p.get("formattedAddress"),
                    "location": {
                        "lat": p.get("location", {}).get("latitude"),
                        "lng": p.get("location", {}).get("longitude"),
                    },
                    "display_name": p.get("displayName", {}).get("text"),
                }
        return {"error": f"No coordinates found for address '{address}'."}
    except Exception as e:
        return {"error": f"Geocoding failed: {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "gym",
    radius_meters: float = 5000.0,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """Search for nearby places of a given type using Places API (New) searchNearby REST endpoint.

    Args:
        latitude: The center latitude for the search.
        longitude: The center longitude for the search.
        place_type: Type of place to find (e.g. 'gym', 'fitness_center', 'park', 'yoga_studio').
        radius_meters: Search radius in meters (default: 5000.0, max: 50000.0).
        max_results: Maximum number of places to return (default: 5, max: 20).

    Returns:
        A list of nearby places with name, formatted address, and coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }

    body = json.dumps({
        "includedTypes": [place_type],
        "maxResultCount": min(max_results, 20),
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": float(radius_meters),
            }
        },
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))

        results = []
        for p in payload.get("places", []):
            results.append({
                "name": p.get("displayName", {}).get("text", "Unknown"),
                "address": p.get("formattedAddress", ""),
                "location": {
                    "latitude": p.get("location", {}).get("latitude"),
                    "longitude": p.get("location", {}).get("longitude"),
                },
            })

        return results if results else [{"message": f"No {place_type} found within {radius_meters}m."}]
    except Exception as e:
        return [{"error": f"Places search failed: {str(e)}"}]


from google import genai
from google.adk.tools import ToolContext
from google.cloud import storage
import base64
import uuid

BUCKET_NAME = "fitness-coach-media-qwiklabs-gcp-04-f27982afaad3"

# Initialize GenAI Client in global region with Vertex AI
genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
storage_client = storage.Client(project=PROJECT_ID)


async def generate_workout_illustration(prompt: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Generate an illustrative image for a workout, exercise, or fitness achievement.

    Uses the gemini-3.1-flash-lite-image model in the global region.
    Saves the image as an artifact in the session and uploads it directly to Cloud Storage,
    returning its public https URL.

    Args:
        prompt: Detailed description of the image to generate (e.g. 'A fitness athlete performing kettlebell swings in a bright modern gym').

    Returns:
        A dictionary with the public image URL, filename, and status.
    """
    try:
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )

        img_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    img_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not img_bytes:
            return {"error": "No image data was generated by the model."}

        # 1. Save artifact to ToolContext
        short_id = uuid.uuid4().hex[:8]
        extension = "jpg" if "jpeg" in mime_type else "png"
        filename = f"workout_image_{short_id}.{extension}"

        artifact_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload directly to public Cloud Storage bucket without writing to local disk
        bucket = storage_client.bucket(BUCKET_NAME)
        blob_path = f"generated_images/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(img_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_path}"

        return {
            "status": "success",
            "filename": filename,
            "public_url": public_url,
            "prompt": prompt,
        }
    except Exception as e:
        return {"error": f"Image generation failed: {str(e)}"}


async def generate_workout_video(prompt: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Generate a short instructional video for a workout or exercise routine item.

    Uses Google's Omni model (gemini-omni-flash-preview) in the global region.
    Saves the video as an artifact using tool_context.save_artifact so it appears
    in the Playground Artifacts panel, and uploads the video bytes directly to the
    public Cloud Storage bucket without writing to local disk, returning its public https URL.

    Args:
        prompt: Description of the workout exercise or motion to visualize (e.g. 'A fitness athlete performing clean kettlebell swings in a bright modern gym').

    Returns:
        A dictionary with the public video URL, filename, and status.
    """
    try:
        interaction = genai_client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
            response_format=[{"type": "video"}],
        )

        video_bytes = None
        mime_type = "video/mp4"

        output_video = getattr(interaction, "output_video", None)
        if output_video:
            if isinstance(output_video, dict) and output_video.get("data"):
                raw_data = output_video["data"]
                video_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data
                mime_type = output_video.get("mime_type") or "video/mp4"
            elif hasattr(output_video, "data") and output_video.data:
                raw_data = output_video.data
                video_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data
                mime_type = getattr(output_video, "mime_type", "video/mp4")

        # Fallback inspection of steps
        if not video_bytes and hasattr(interaction, "steps"):
            for step in getattr(interaction, "steps", []):
                content = getattr(step, "content", []) or []
                for item in content:
                    if getattr(item, "type", "") == "video" or (isinstance(item, dict) and item.get("type") == "video"):
                        raw = getattr(item, "data", None) if hasattr(item, "data") else item.get("data")
                        if raw:
                            video_bytes = base64.b64decode(raw) if isinstance(raw, str) else raw
                            mime_type = getattr(item, "mime_type", "video/mp4") if hasattr(item, "mime_type") else item.get("mime_type", "video/mp4")
                            break
                if video_bytes:
                    break

        if not video_bytes:
            return {"error": "No video data was generated by the gemini-omni-flash-preview model."}

        # 1. Save artifact to ToolContext
        short_id = uuid.uuid4().hex[:8]
        filename = f"workout_video_{short_id}.mp4"

        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload directly to public Cloud Storage bucket without writing to local disk
        bucket = storage_client.bucket(BUCKET_NAME)
        blob_path = f"generated_videos/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_path}"

        return {
            "status": "success",
            "filename": filename,
            "public_url": public_url,
            "prompt": prompt,
        }
    except Exception as e:
        return {"error": f"Video generation failed: {str(e)}"}


import json
from pathlib import Path
from google.adk.code_executors import AgentEngineSandboxCodeExecutor

# Load agent engine resource name from deployment_metadata.json if present
def _get_agent_engine_resource_name() -> Optional[str]:
    metadata_path = Path(__file__).resolve().parent.parent / "deployment_metadata.json"
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            pending_op = meta.get("pending_operation", {}).get("operation_name", "")
            if "/operations/" in pending_op:
                return pending_op.split("/operations/")[0]
        except Exception:
            pass
    return "projects/200973147793/locations/us-east1/reasoningEngines/6744314164824506368"

_agent_engine_res = _get_agent_engine_resource_name()
code_executor = AgentEngineSandboxCodeExecutor(agent_engine_resource_name=_agent_engine_res)

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool


# WRITE: after each turn, send the session to Memory Bank for extraction.
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


from .a2ui_utils import a2ui_callback

try:
    from a2ui.schema.manager import A2uiSchemaManager
    from a2ui.basic_catalog.provider import BasicCatalog

    schema_manager = A2uiSchemaManager(
        version="0.8",
        catalogs=[BasicCatalog.get_config("0.8")],
    )

    instruction = schema_manager.generate_system_prompt(
        role_description=(
            "You are Neerja's personal fitness coach. You actively remember the user's stated fitness goals, "
            "injuries, preferences, allergies (food, environmental, and medical), and dietary restrictions "
            "across conversations and always use them to personalize your recommendations, nutrition guidance, and coaching. "
            "You help her choose workouts from the catalog, customize routines, calculate heart rate training zones, "
            "search for specific exercises in the open exercise database, find local gyms or fitness spots using Maps Places, "
            "generate workout illustrations, and log completed workout sessions. "
            "You also have a secure Python sandbox code executor to perform precise fitness calculations, BMI/BMR statistics, "
            "and numerical modeling by running Python code. "
            "Use list_workouts and get_workout_details to inspect available routines, "
            "search_public_exercises to look up movements or equipment variations, "
            "geocode_address and find_nearby_places to discover local fitness facilities, "
            "generate_workout_illustration to produce visual guides or motivational workout posters, "
            "generate_workout_video to produce short instructional exercise videos using gemini-omni-flash-preview, "
            "calculate_heart_rate_zones to provide target heart rate training intensity, and "
            "log_completed_workout and get_recent_workout_logs to record and check her workout history. "
            "Be encouraging, concise, and focused on her fitness progress."
        ),
        workflow_description="Analyze the request and return structured UI when appropriate.",
        ui_description=(
            "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
            "Never nest a Card inside a Card. "
            "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
            "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
            "nothing in adk web). "
            "You may include one Image component, but only when you have a public https "
            "URL for the image (for example the URL an image tool returns after uploading "
            "to a public bucket). Set the Image url to that exact https link, for example "
            "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
            "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
            "not have a public URL, add a short Text line noting the image instead. "
            "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
            "headings and emphasis. "
            "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
            "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
        ),
        include_schema=True,
        include_examples=True,
    )
except ImportError:
    from .a2ui_instruction import INSTRUCTION as instruction

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        list_workouts,
        get_workout_details,
        search_public_exercises,
        calculate_heart_rate_zones,
        geocode_address,
        find_nearby_places,
        generate_workout_illustration,
        generate_workout_video,
        log_completed_workout,
        get_recent_workout_logs,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
