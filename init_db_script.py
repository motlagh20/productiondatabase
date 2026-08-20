
import sys
import os

# Add samples to path to import app
sys.path.append(os.path.join(os.getcwd(), 'samples'))

try:
    from app import init_db, ensure_dev_bootstrap
    print("Initializing database...")
    init_db()
    print("Bootstrapping dev defaults...")
    ensure_dev_bootstrap()
    print("Database initialized successfully.")
except ImportError as e:
    print(f"Error importing from samples.app: {e}")
except Exception as e:
    print(f"Error initializing DB: {e}")
