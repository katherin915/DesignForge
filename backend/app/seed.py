from sqlmodel import Session, select
from app.db import engine
from app.models import Problem

PROBLEMS = [
    {
        "title": "Parking Lot System",
        "description": (
            "Design a parking lot that supports multiple floors and multiple vehicle "
            "types (motorcycle, car, truck). Vehicles should be assigned to an "
            "appropriately-sized spot. Support entry, exit, and fee calculation "
            "based on duration."
        ),
        "difficulty": "medium",
    },
    {
        "title": "Vending Machine",
        "description": (
            "Design a vending machine that holds multiple products with limited stock, "
            "accepts coins/notes, dispenses change, and handles out-of-stock and "
            "insufficient-payment cases."
        ),
        "difficulty": "easy",
    },
    {
        "title": "Elevator System",
        "description": (
            "Design an elevator control system for a building with multiple elevators "
            "and floors. Handle request scheduling (which elevator responds to a call), "
            "direction, and door state."
        ),
        "difficulty": "hard",
    },
]


def seed():
    with Session(engine) as session:
        existing = session.exec(select(Problem)).first()
        if existing:
            print("Problems already seeded, skipping.")
            return
        for p in PROBLEMS:
            session.add(Problem(**p))
        session.commit()
        print(f"Seeded {len(PROBLEMS)} problems.")


if __name__ == "__main__":
    from app.db import init_db
    init_db()
    seed()