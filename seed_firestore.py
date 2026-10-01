#!/usr/bin/env python3
"""Seed script for fitness-coach Firestore database."""
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-f27982afaad3"

SAMPLE_WORKOUTS = [
    {
        "id": "hiit-full-body",
        "title": "Full-Body HIIT Burner",
        "description": "High-intensity interval routine targeting full-body strength and endurance with minimal equipment.",
        "difficulty": "Intermediate",
        "duration_minutes": 25,
        "equipment": ["Bodyweight", "Jump rope"],
        "target_muscles": ["Full Body", "Cardio", "Core"],
        "exercises": [
            {"name": "Jumping Jacks", "duration_sec": 45, "rest_sec": 15},
            {"name": "Bodyweight Squats", "duration_sec": 45, "rest_sec": 15},
            {"name": "Push-ups", "duration_sec": 45, "rest_sec": 15},
            {"name": "Mountain Climbers", "duration_sec": 45, "rest_sec": 15},
            {"name": "High Knees", "duration_sec": 45, "rest_sec": 15},
        ],
        "estimated_calories": 250,
    },
    {
        "id": "dumbbells-upper-body",
        "title": "Upper Body Strength & Tone",
        "description": "Dumbbell-focused workout to build upper body posture, shoulder stability, and arms.",
        "difficulty": "Beginner to Intermediate",
        "duration_minutes": 35,
        "equipment": ["Dumbbells", "Exercise Mat"],
        "target_muscles": ["Chest", "Shoulders", "Back", "Arms"],
        "exercises": [
            {"name": "Dumbbell Overhead Press", "sets": 3, "reps": 12},
            {"name": "Dumbbell Rows", "sets": 3, "reps": 12},
            {"name": "Floor Chest Press", "sets": 3, "reps": 12},
            {"name": "Bicep Curls to Lateral Raise", "sets": 3, "reps": 10},
        ],
        "estimated_calories": 220,
    },
    {
        "id": "core-mobility-flow",
        "title": "Core Strength & Mobility Flow",
        "description": "Low-impact core conditioning and spinal mobility flow to enhance core stability.",
        "difficulty": "All Levels",
        "duration_minutes": 20,
        "equipment": ["Yoga Mat"],
        "target_muscles": ["Abs", "Obliques", "Lower Back", "Glutes"],
        "exercises": [
            {"name": "Deadbug", "sets": 3, "reps": 10},
            {"name": "Bird Dog", "sets": 3, "reps": 10},
            {"name": "Forearm Plank", "duration_sec": 60, "rest_sec": 20},
            {"name": "Glute Bridges", "sets": 3, "reps": 15},
        ],
        "estimated_calories": 130,
    },
    {
        "id": "lower-body-power",
        "title": "Lower Body Glutes & Legs Power",
        "description": "Targeted leg and posterior chain strengthening routine for endurance and power.",
        "difficulty": "Intermediate",
        "duration_minutes": 30,
        "equipment": ["Resistance Band", "Dumbbells"],
        "target_muscles": ["Quads", "Hamstrings", "Glutes", "Calves"],
        "exercises": [
            {"name": "Goblet Squats", "sets": 3, "reps": 12},
            {"name": "Romanian Deadlifts", "sets": 3, "reps": 12},
            {"name": "Walking Lunges", "sets": 3, "reps": 20},
            {"name": "Banded Glute Bridges", "sets": 3, "reps": 15},
        ],
        "estimated_calories": 240,
    },
]

def seed_database():
    print(f"Connecting to Firestore for project '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection("workouts")

    for item in SAMPLE_WORKOUTS:
        doc_id = item["id"]
        doc_ref = collection.document(doc_id)
        doc_ref.set(item)
        print(f"Seeded workout: {item['title']} (id: {doc_id})")

    print("Firestore seeding complete!")

if __name__ == "__main__":
    seed_database()
