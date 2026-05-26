"""
Seed the persistent data volume on first deploy.

When running on Fly.io, the data directory is a persistent volume mounted at /data.
On first deploy, this volume is empty. This script copies the initial data files
(routine-cards, baby-cards, score_bests, etc.) from the repo's data/ directory
into the persistent volume so the app has a starting state.

Subsequent deploys skip the broad copy because the volume already has data.
Small app-owned data migrations/seeds that are safe to run repeatedly can still
run at the end of this function.
"""
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DATA_DIR = os.path.join(BASE_DIR, "data")
PERSISTENT_DATA_DIR = os.environ.get("LM_DATA_DIR", "")


def _run_idempotent_app_seeds():
    try:
        from services.may25_recipe_seed import seed_may25_recipes
        seed_may25_recipes()
    except Exception as exc:
        print(f"[seed] May 25 recipe seed skipped/failed: {exc}")


def seed():
    if not PERSISTENT_DATA_DIR or PERSISTENT_DATA_DIR == REPO_DATA_DIR:
        print("[seed] Running locally, no broad volume seeding needed.")
        _run_idempotent_app_seeds()
        return

    # Check if volume already has data
    marker = os.path.join(PERSISTENT_DATA_DIR, ".seeded")
    if os.path.exists(marker):
        print("[seed] Persistent volume already seeded, skipping broad copy.")
        _run_idempotent_app_seeds()
        return

    print(f"[seed] Seeding persistent volume at {PERSISTENT_DATA_DIR} ...")
    os.makedirs(PERSISTENT_DATA_DIR, exist_ok=True)

    # Copy everything from repo data/ to persistent volume
    for item in os.listdir(REPO_DATA_DIR):
        src = os.path.join(REPO_DATA_DIR, item)
        dst = os.path.join(PERSISTENT_DATA_DIR, item)
        if os.path.isdir(src):
            if not os.path.exists(dst):
                shutil.copytree(src, dst)
                print(f"  Copied directory: {item}")
        else:
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                print(f"  Copied file: {item}")

    # Write marker so we don't re-seed the broad copy
    with open(marker, "w") as f:
        f.write("seeded\n")
    print("[seed] Broad seed done.")
    _run_idempotent_app_seeds()


if __name__ == "__main__":
    seed()
