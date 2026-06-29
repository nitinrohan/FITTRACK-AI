"""Seed data for the system exercise library.

Run via: python -m app.seeds.exercises
Or called automatically by the startup seed script.

These are the 60 most common exercises across strength, cardio, and flexibility.
System exercises (is_system=True) are global and visible to all users.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.repositories import exercise_repository

logger = logging.getLogger(__name__)

SYSTEM_EXERCISES: list[dict[str, Any]] = [
    # ── Strength - Chest ──────────────────────────────────────────────
    {
        "name": "Barbell Bench Press",
        "category": "strength",
        "equipment": "barbell",
        "muscle_groups": ["chest", "triceps", "shoulders"],
        "description": "Compound pressing movement targeting the chest.",
        "instructions": "Lie on a flat bench. Grip the bar slightly wider than shoulder-width. Lower to mid-chest, then press back up.",
    },
    {
        "name": "Dumbbell Bench Press",
        "category": "strength",
        "equipment": "dumbbell",
        "muscle_groups": ["chest", "triceps", "shoulders"],
        "description": "Pressing movement with dumbbells for greater range of motion.",
        "instructions": "Lie on a flat bench holding dumbbells at chest height. Press up until arms are extended, then lower slowly.",
    },
    {
        "name": "Incline Barbell Bench Press",
        "category": "strength",
        "equipment": "barbell",
        "muscle_groups": ["upper chest", "triceps", "shoulders"],
        "description": "Upper-chest focused bench press variation.",
        "instructions": "Set bench to 30-45 degrees. Grip bar slightly wider than shoulders and press with focus on upper chest.",
    },
    {
        "name": "Push-Up",
        "category": "strength",
        "equipment": "bodyweight",
        "muscle_groups": ["chest", "triceps", "shoulders", "core"],
        "description": "Classic bodyweight chest exercise.",
        "instructions": "Place hands shoulder-width apart. Lower your chest to the floor then push back up, keeping body straight.",
    },
    {
        "name": "Cable Chest Fly",
        "category": "strength",
        "equipment": "cable",
        "muscle_groups": ["chest"],
        "description": "Isolation fly movement using cable pulleys.",
        "instructions": "Set cables at shoulder height. Step forward and bring hands together in a hugging arc.",
    },
    # ── Strength - Back ───────────────────────────────────────────────
    {
        "name": "Barbell Deadlift",
        "category": "strength",
        "equipment": "barbell",
        "muscle_groups": ["hamstrings", "glutes", "lower back", "traps", "forearms"],
        "description": "The fundamental hip-hinge movement. Works the entire posterior chain.",
        "instructions": "Stand with feet hip-width. Hinge at hips and grip the bar. Drive through the floor while keeping a neutral spine.",
    },
    {
        "name": "Pull-Up",
        "category": "strength",
        "equipment": "bodyweight",
        "muscle_groups": ["lats", "biceps", "rear delts"],
        "description": "Overhand bodyweight vertical pull.",
        "instructions": "Hang from a bar with hands shoulder-width apart (overhand). Pull until chin is over the bar.",
    },
    {
        "name": "Chin-Up",
        "category": "strength",
        "equipment": "bodyweight",
        "muscle_groups": ["lats", "biceps"],
        "description": "Underhand vertical pull - greater bicep emphasis than pull-up.",
        "instructions": "Hang from a bar with palms facing you. Pull until chin clears the bar.",
    },
    {
        "name": "Barbell Row",
        "category": "strength",
        "equipment": "barbell",
        "muscle_groups": ["lats", "rhomboids", "rear delts", "biceps"],
        "description": "Horizontal pulling movement for back thickness.",
        "instructions": "Hinge forward at 45°. Pull bar to lower chest, squeezing shoulder blades together.",
    },
    {
        "name": "Seated Cable Row",
        "category": "strength",
        "equipment": "cable",
        "muscle_groups": ["lats", "rhomboids", "biceps"],
        "description": "Horizontal cable pull for mid-back development.",
        "instructions": "Sit at cable row machine. Pull handle to your abdomen, keeping elbows close and back upright.",
    },
    {
        "name": "Lat Pulldown",
        "category": "strength",
        "equipment": "cable",
        "muscle_groups": ["lats", "biceps"],
        "description": "Machine-assisted vertical pull targeting the lats.",
        "instructions": "Grab bar wider than shoulder-width. Pull down to upper chest while leaning back slightly.",
    },
    {
        "name": "Dumbbell Row",
        "category": "strength",
        "equipment": "dumbbell",
        "muscle_groups": ["lats", "rhomboids", "biceps"],
        "description": "Single-arm row for unilateral back development.",
        "instructions": "Plant one knee on a bench. Pull the dumbbell to your hip, keeping your elbow close.",
    },
    # ── Strength - Shoulders ──────────────────────────────────────────
    {
        "name": "Overhead Press",
        "category": "strength",
        "equipment": "barbell",
        "muscle_groups": ["shoulders", "triceps", "upper traps"],
        "description": "Standing or seated barbell press overhead.",
        "instructions": "Hold bar at shoulder height. Press straight overhead until arms are locked out.",
    },
    {
        "name": "Dumbbell Shoulder Press",
        "category": "strength",
        "equipment": "dumbbell",
        "muscle_groups": ["shoulders", "triceps"],
        "description": "Seated or standing dumbbell overhead press.",
        "instructions": "Hold dumbbells at shoulder height, elbows at 90°. Press up until arms are extended.",
    },
    {
        "name": "Lateral Raise",
        "category": "strength",
        "equipment": "dumbbell",
        "muscle_groups": ["lateral deltoid"],
        "description": "Isolation movement for shoulder width.",
        "instructions": "Hold dumbbells at your sides. Raise arms to shoulder height with a slight bend in the elbows.",
    },
    {
        "name": "Face Pull",
        "category": "strength",
        "equipment": "cable",
        "muscle_groups": ["rear delts", "external rotators", "traps"],
        "description": "Cable exercise for rear delt and rotator cuff health.",
        "instructions": "Set cable at head height with rope attachment. Pull rope to your face, flaring elbows out.",
    },
    # ── Strength - Arms ───────────────────────────────────────────────
    {
        "name": "Barbell Curl",
        "category": "strength",
        "equipment": "barbell",
        "muscle_groups": ["biceps", "forearms"],
        "description": "Standing bicep curl with a barbell.",
        "instructions": "Stand with bar at arm's length. Curl up to shoulder height keeping elbows fixed.",
    },
    {
        "name": "Dumbbell Curl",
        "category": "strength",
        "equipment": "dumbbell",
        "muscle_groups": ["biceps"],
        "description": "Alternating or simultaneous dumbbell curl.",
        "instructions": "Hold dumbbells at your sides. Curl one or both arms to shoulder height, supinating at the top.",
    },
    {
        "name": "Hammer Curl",
        "category": "strength",
        "equipment": "dumbbell",
        "muscle_groups": ["biceps", "brachialis", "forearms"],
        "description": "Neutral-grip curl targeting the brachialis and forearms.",
        "instructions": "Hold dumbbells with palms facing each other. Curl to shoulder height.",
    },
    {
        "name": "Tricep Pushdown",
        "category": "strength",
        "equipment": "cable",
        "muscle_groups": ["triceps"],
        "description": "Cable isolation for the triceps.",
        "instructions": "Grip a bar or rope at chest height. Push down until arms are straight, elbows fixed at sides.",
    },
    {
        "name": "Skull Crusher",
        "category": "strength",
        "equipment": "ez_bar",
        "muscle_groups": ["triceps"],
        "description": "Lying tricep extension.",
        "instructions": "Lie on a bench. Hold bar above chest and lower to forehead by bending at the elbows, then extend.",
    },
    {
        "name": "Dip",
        "category": "strength",
        "equipment": "bodyweight",
        "muscle_groups": ["triceps", "chest", "shoulders"],
        "description": "Parallel bar dip for triceps and chest.",
        "instructions": "Grip parallel bars and lower your body until shoulders are below elbows. Press back up.",
    },
    # ── Strength - Legs ───────────────────────────────────────────────
    {
        "name": "Barbell Back Squat",
        "category": "strength",
        "equipment": "barbell",
        "muscle_groups": ["quads", "glutes", "hamstrings", "core"],
        "description": "King of lower body exercises. High-bar or low-bar variation.",
        "instructions": "Bar rests on traps. Feet shoulder-width apart. Descend until thighs are parallel, then drive up.",
    },
    {
        "name": "Goblet Squat",
        "category": "strength",
        "equipment": "dumbbell",
        "muscle_groups": ["quads", "glutes", "core"],
        "description": "Front-loaded squat great for beginners and mobility.",
        "instructions": "Hold a dumbbell at chest height. Squat down keeping your chest upright and elbows inside your knees.",
    },
    {
        "name": "Romanian Deadlift",
        "category": "strength",
        "equipment": "barbell",
        "muscle_groups": ["hamstrings", "glutes", "lower back"],
        "description": "Hip-hinge movement emphasising the hamstrings.",
        "instructions": "Hold bar at hip level. Hinge forward keeping legs mostly straight until you feel a hamstring stretch.",
    },
    {
        "name": "Leg Press",
        "category": "strength",
        "equipment": "machine",
        "muscle_groups": ["quads", "glutes", "hamstrings"],
        "description": "Machine-based lower-body press.",
        "instructions": "Sit in the machine. Press the platform away until legs are extended (don't lock out). Lower slowly.",
    },
    {
        "name": "Lunge",
        "category": "strength",
        "equipment": "bodyweight",
        "muscle_groups": ["quads", "glutes", "hamstrings"],
        "description": "Unilateral leg exercise for balance and strength.",
        "instructions": "Step forward and lower your back knee toward the floor. Push back up and repeat on the other leg.",
    },
    {
        "name": "Bulgarian Split Squat",
        "category": "strength",
        "equipment": "dumbbell",
        "muscle_groups": ["quads", "glutes"],
        "description": "Rear-foot-elevated split squat. Excellent for quad and glute development.",
        "instructions": "Rest rear foot on a bench. Lower front knee toward the floor, then drive up.",
    },
    {
        "name": "Hip Thrust",
        "category": "strength",
        "equipment": "barbell",
        "muscle_groups": ["glutes", "hamstrings"],
        "description": "Best isolation movement for the glutes.",
        "instructions": "Sit with upper back on a bench, bar over hips. Drive hips up by squeezing glutes at the top.",
    },
    {
        "name": "Leg Curl",
        "category": "strength",
        "equipment": "machine",
        "muscle_groups": ["hamstrings"],
        "description": "Lying or seated hamstring isolation machine.",
        "instructions": "Lie face down. Curl the pad toward your glutes, hold briefly, then lower.",
    },
    {
        "name": "Leg Extension",
        "category": "strength",
        "equipment": "machine",
        "muscle_groups": ["quads"],
        "description": "Quad isolation machine.",
        "instructions": "Sit in the machine. Extend legs until straight, then lower slowly.",
    },
    {
        "name": "Calf Raise",
        "category": "strength",
        "equipment": "machine",
        "muscle_groups": ["calves"],
        "description": "Standing or seated calf isolation.",
        "instructions": "Press through the balls of your feet to raise your heels as high as possible. Lower fully.",
    },
    # ── Strength - Core ───────────────────────────────────────────────
    {
        "name": "Plank",
        "category": "strength",
        "equipment": "bodyweight",
        "muscle_groups": ["core", "shoulders"],
        "description": "Isometric core stability exercise.",
        "instructions": "Hold a push-up position on forearms. Keep hips level and body in a straight line.",
    },
    {
        "name": "Crunch",
        "category": "strength",
        "equipment": "bodyweight",
        "muscle_groups": ["abs"],
        "description": "Basic abdominal crunch.",
        "instructions": "Lie on your back with knees bent. Curl your shoulders toward your knees, then lower.",
    },
    {
        "name": "Hanging Leg Raise",
        "category": "strength",
        "equipment": "bodyweight",
        "muscle_groups": ["abs", "hip flexors"],
        "description": "Hanging core exercise for the lower abs.",
        "instructions": "Hang from a pull-up bar. Raise legs to 90° (or higher), then lower with control.",
    },
    {
        "name": "Ab Wheel Rollout",
        "category": "strength",
        "equipment": "other",
        "muscle_groups": ["abs", "core", "shoulders"],
        "description": "Challenging anti-extension core movement.",
        "instructions": "Kneel holding the ab wheel. Roll forward until body is extended, then pull back using your abs.",
    },
    # ── Cardio ────────────────────────────────────────────────────────
    {
        "name": "Running",
        "category": "cardio",
        "equipment": "none",
        "muscle_groups": ["quads", "hamstrings", "calves", "glutes"],
        "description": "Outdoor or treadmill running.",
        "instructions": "Maintain an upright posture, relaxed arms, and a cadence of 170-180 steps/min.",
    },
    {
        "name": "Cycling",
        "category": "cardio",
        "equipment": "machine",
        "muscle_groups": ["quads", "hamstrings", "calves"],
        "description": "Stationary bike or outdoor cycling.",
        "instructions": "Set seat height so the knee has a slight bend at the bottom of the pedal stroke.",
    },
    {
        "name": "Rowing",
        "category": "cardio",
        "equipment": "machine",
        "muscle_groups": ["back", "legs", "arms", "core"],
        "description": "Rowing ergometer - full-body cardio.",
        "instructions": "Drive with legs first, then lean back, then pull arms to your chest. Reverse on recovery.",
    },
    {
        "name": "Jump Rope",
        "category": "cardio",
        "equipment": "other",
        "muscle_groups": ["calves", "shoulders", "core"],
        "description": "Skipping rope for cardiovascular conditioning.",
        "instructions": "Jump with feet together or alternating. Keep elbows close and rotate the rope with wrists.",
    },
    {
        "name": "Burpee",
        "category": "cardio",
        "equipment": "bodyweight",
        "muscle_groups": ["full body"],
        "description": "High-intensity full-body conditioning movement.",
        "instructions": "From standing: squat down, jump feet back to a push-up, do a push-up, jump feet forward, then jump up.",
    },
    {
        "name": "Elliptical",
        "category": "cardio",
        "equipment": "machine",
        "muscle_groups": ["quads", "hamstrings", "glutes"],
        "description": "Low-impact cardio on an elliptical trainer.",
        "instructions": "Maintain an upright posture and steady stride. Use the handles to engage the upper body.",
    },
    {
        "name": "Stair Climber",
        "category": "cardio",
        "equipment": "machine",
        "muscle_groups": ["glutes", "quads", "calves"],
        "description": "Climbing stairs on a step machine.",
        "instructions": "Stand tall and drive through your whole foot on each step. Avoid leaning on the handles.",
    },
    {
        "name": "Swimming",
        "category": "cardio",
        "equipment": "none",
        "muscle_groups": ["full body"],
        "description": "Full-body low-impact cardio in water.",
        "instructions": "Choose a stroke (freestyle, breaststroke, etc.) and maintain a steady breathing rhythm.",
    },
    # ── Flexibility / Mobility ─────────────────────────────────────────
    {
        "name": "Hip Flexor Stretch",
        "category": "flexibility",
        "equipment": "none",
        "muscle_groups": ["hip flexors"],
        "description": "Kneeling lunge stretch for tight hip flexors.",
        "instructions": "Kneel on one knee. Push hips forward gently until you feel a stretch in the front of the back hip.",
    },
    {
        "name": "Hamstring Stretch",
        "category": "flexibility",
        "equipment": "none",
        "muscle_groups": ["hamstrings"],
        "description": "Seated or standing hamstring lengthening.",
        "instructions": "Sit with one leg extended. Reach toward your foot while keeping your back straight.",
    },
    {
        "name": "Chest Opener Stretch",
        "category": "flexibility",
        "equipment": "none",
        "muscle_groups": ["chest", "shoulders"],
        "description": "Doorway or band stretch to open the chest.",
        "instructions": "Stand in a doorway. Place forearms on the frame and lean forward until you feel a chest stretch.",
    },
    {
        "name": "Child's Pose",
        "category": "flexibility",
        "equipment": "none",
        "muscle_groups": ["lower back", "hips", "shoulders"],
        "description": "Restorative yoga pose for back and hip release.",
        "instructions": "Kneel and sit back on your heels. Extend arms forward on the floor and relax.",
    },
    {
        "name": "Pigeon Pose",
        "category": "flexibility",
        "equipment": "none",
        "muscle_groups": ["glutes", "hip external rotators"],
        "description": "Deep hip opener from yoga.",
        "instructions": "From all-fours, bring one shin forward parallel to the mat. Lower hips toward the floor.",
    },
    {
        "name": "Cat-Cow",
        "category": "flexibility",
        "equipment": "none",
        "muscle_groups": ["spine", "core"],
        "description": "Spinal mobility exercise pairing flexion and extension.",
        "instructions": "On hands and knees: inhale and arch the back (cow), exhale and round the spine (cat).",
    },
    {
        "name": "Thoracic Rotation",
        "category": "flexibility",
        "equipment": "none",
        "muscle_groups": ["thoracic spine", "obliques"],
        "description": "Rotational mobility for the upper back.",
        "instructions": "Lie on your side with knees at 90°. Rotate your top arm and shoulder open toward the floor.",
    },
    {
        "name": "Foam Roll - Quads",
        "category": "flexibility",
        "equipment": "other",
        "muscle_groups": ["quads"],
        "description": "Self-myofascial release for the quadriceps.",
        "instructions": "Lie face down with the foam roller under your thighs. Roll slowly from hip to knee.",
    },
]


def seed_exercises(db: Session) -> int:
    """Insert system exercises if none exist. Returns the number inserted."""
    if exercise_repository.system_exists(db):
        logger.info("System exercises already seeded - skipping")
        return 0

    inserted = 0
    for data in SYSTEM_EXERCISES:
        exercise_repository.create(
            db,
            name=data["name"],
            category=data["category"],
            equipment=data["equipment"],
            description=data.get("description"),
            instructions=data.get("instructions"),
            muscle_groups=data.get("muscle_groups"),
            is_system=True,
            user_id=None,
        )
        inserted += 1

    db.commit()
    logger.info("Seeded %d system exercises", inserted)
    return inserted


if __name__ == "__main__":
    import logging

    from app.database import get_session_factory

    logging.basicConfig(level=logging.INFO)
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        n = seed_exercises(session)
        print(f"Done - {n} exercises inserted.")
