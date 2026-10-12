"""36 fictional records. Stable keys make loading repeatable without duplicates."""
from datetime import date, timedelta

from ai_service import AIService
from database import Database
from memory_service import MemoryService
from models import MemoryInput

THEMES = [
    ("Basketball", "University court", [
        "Basketball practice with friends. I worked on free throws for twenty minutes.",
        "Played basketball with friends after class and practiced passing.",
        "At basketball practice, we worked on defending together.",
        "Joined a friendly basketball match at the university court.",
        "Basketball practice: I stayed after the match to practice three-pointers.",
        "For the first time, I made a buzzer-beating three-pointer in a basketball match with friends!",
    ]),
    ("Guitar", "Dorm room", [
        "Started learning guitar again and practiced the C and G chords.",
        "Guitar practice today: slowly changing from C to G.",
        "Tried the F chord on my guitar. My fingers needed a break.",
        "For the first time, I changed to the F chord cleanly on guitar.",
        "Practiced guitar with a metronome for fifteen minutes.",
        "For the first time, I played an entire song on guitar without stopping!",
    ]),
    ("Coursework", "Campus library", [
        "Reviewed lecture notes for my university algorithms coursework.",
        "Worked on a database assignment in the campus library.",
        "Study group for our university coursework: compared graph traversal notes.",
        "Finished the first draft of my university coursework report.",
        "Prepared for the algorithms exam with practice questions.",
        "Finally completed my database coursework project and submitted the report.",
    ]),
    ("Travel", "Kyoto", [
        "Planned a trip to Kyoto with friends and wrote down a short itinerary.",
        "On our Kyoto trip with friends, we walked along the river.",
        "Travel day in Kyoto: visited a small bookstore with friends.",
        "During our Kyoto trip, friends and I shared lunch near the station.",
        "Travel notes from Kyoto: watched the sunset by the river with friends.",
        "Our Kyoto trip ended today. I saved the train tickets in my notebook.",
    ]),
    ("Programming", "Computer lab", [
        "Started a small Python programming project to organize reading notes.",
        "Coding after class: wrote my first data import function in Python.",
        "Spent an hour debugging my Python programming project.",
        "For the first time, all tests passed in my Python programming project.",
        "Showed friends a working version of my Python programming project.",
        "Finally finished the first version of my Python programming project!",
    ]),
    ("Everyday", None, [
        "Bought a new notebook at the corner shop.",
        "Met friends for tea and talked about a film.",
        "Watered the plant on my windowsill.",
        "Took the bus home and read a few pages of a novel.",
        "Had lunch with friends at a nearby cafe.",
        "Tidied my desk and found an old postcard.",
    ]),
]


def load_demo(db, media_dir):
    service = MemoryService(db, media_dir, AIService())  # Always offline, even when cloud is selected.
    added = 0
    for theme_index, (theme, location, records) in enumerate(THEMES):
        for week, content in enumerate(records):
            key = f"omoide-demo-v1-{theme_index}-{week}"
            if db.has_demo_key(key):
                continue
            occurred = date(2026, 9, 1) + timedelta(days=week * 7 + theme_index)
            service.create(MemoryInput(title=f"{theme} · {week + 1}", content=content, occurred_at=occurred, location=location), synthetic=True, demo_key=key)
            added += 1
    return added


if __name__ == "__main__":
    from config import data_dir
    root = data_dir()
    print(f"Added {load_demo(Database(root / 'omoide.sqlite3'), root / 'media')} Synthetic Demo Data records.")
