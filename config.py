"""
Configuration settings for the Event Registration System.
"""
import os
from pathlib import Path
APP_TITLE = "Spandan 1.0"
APP_ICON = 'src/ndim.png'
EVENT_ICON = 'src/SPANDAN.webp'
THEME_COLOR = 'red'
ENABLE_DARK_MODE = False
# Base directory
BASE_DIR = Path(__file__).parent

# Data directory
DATA_DIR = os.path.join(BASE_DIR, "data")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# Database settings
DATABASE_PATH = os.path.join(DATA_DIR, "database.db")

# Session configuration
SESSION_EXPIRY = 30  # minutes

# Create necessary directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

# App settings
APP_NAME = "Spandan Registration System"
PRIMARY_COLOR = "#1E88E5"
SECONDARY_COLOR = "#FFC107"
SUCCESS_COLOR = "#4CAF50"
WARNING_COLOR = "#FF9800"
DANGER_COLOR = "#F44336"

# Role definitions
ROLES = {
    "admin": {
        "name": "Admin",
        "permissions": ["manage_users", "manage_events", "view_dashboard", "upload_data", "manage_registration"],
        "description": "Full access to all features"
    },
    "data_manager": {
        "name": "Data Manager", 
        "permissions": ["upload_data", "view_dashboard"],
        "description": "Can upload registration data"
    },
    "registration": {
        "name": "Registration Team",
        "permissions": ["manage_registration", "view_dashboard"],
        "description": "Can mark attendance and update participant info"
    },
    "viewer": {
        "name": "Viewer",
        "permissions": ["view_dashboard"],
        "description": "Can view dashboards only"
    }
}

# Default admin account (for initial setup)
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",  # This will be hashed during initialization
    "role": "admin"
}