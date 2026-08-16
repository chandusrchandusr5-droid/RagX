import sys
import os

# Add ragx/backend directory to sys.path so app.main imports resolve properly
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.abspath(os.path.join(current_dir, "..", "ragx", "backend"))

if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
