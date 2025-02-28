"""
Authentication system for the Event Registration System.
"""
import streamlit as st
import hashlib
import secrets
import datetime
import time
from functools import wraps
import config
from database import Database

def init_auth():
    """Initialize authentication state in session state if not present."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.role = None
        st.session_state.permissions = []
        st.session_state.auth_timestamp = None
        st.session_state.assigned_event_id = None
    
    # Check for session expiry
    if st.session_state.authenticated and st.session_state.auth_timestamp:
        idle_time = (datetime.datetime.now() - st.session_state.auth_timestamp).seconds / 60
        if idle_time > config.SESSION_EXPIRY:
            logout()
            st.warning(f"Your session has expired after {config.SESSION_EXPIRY} minutes of inactivity.")
            st.rerun()
    
    # Update timestamp on activity
    if st.session_state.authenticated:
        st.session_state.auth_timestamp = datetime.datetime.now()

def hash_password(password):
    """Hash a password using SHA-256."""
    salt = secrets.token_hex(8)
    hasher = hashlib.sha256()
    hasher.update((password + salt).encode('utf-8'))
    password_hash = hasher.hexdigest()
    return f"{salt}${password_hash}"

def verify_password(stored_hash, provided_password):
    """Verify a password against its stored hash."""
    if not stored_hash or '$' not in stored_hash:
        return False
    
    salt, hash_value = stored_hash.split('$')
    hasher = hashlib.sha256()
    hasher.update((provided_password + salt).encode('utf-8'))
    return hasher.hexdigest() == hash_value

def login(username, password):
    """Attempt to log in a user."""
    db = Database()
    user = db.get_user(username)
    
    if user and verify_password(user['password_hash'], password):
        st.session_state.authenticated = True
        st.session_state.user_id = user['id']
        st.session_state.username = user['username']
        st.session_state.role = user['role']
        st.session_state.permissions = config.ROLES[user['role']]['permissions']
        st.session_state.auth_timestamp = datetime.datetime.now()
        st.session_state.assigned_event_id = user['assigned_event_id']
        
        # Update last login timestamp
        db.update_user_last_login(user['id'])
        return True
    
    return False

def logout():
    """Log out the current user."""
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.permissions = []
    st.session_state.auth_timestamp = None
    st.session_state.assigned_event_id = None

def create_initial_admin():
    """Create the initial admin user if no users exist."""
    db = Database()
    # Check if any users exist
    users = db.get_all_users()
    
    if not users:
        # Create default admin
        admin_password_hash = hash_password(config.DEFAULT_ADMIN['password'])
        db.create_user(
            config.DEFAULT_ADMIN['username'],
            admin_password_hash,
            config.DEFAULT_ADMIN['role']
        )
        return True
    
    return False

def requires_auth(permission=None):
    """Decorator to enforce authentication and permission requirements."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            init_auth()
            
            if not st.session_state.authenticated:
                display_login_form()
                return None
            
            if permission and permission not in st.session_state.permissions:
                st.error("You do not have permission to access this feature.")
                return None
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def is_viewer():
    """Check if current user is a viewer (or unauthenticated)."""
    return not st.session_state.authenticated or st.session_state.role == 'viewer'

def display_login_form():
    """Display the login form."""
    st.markdown("## SRS Login🔒")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if login(username, password):
                st.success("Login successful!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid username or password.")

def display_logout_button():
    """Display a logout button if the user is authenticated."""
    if st.session_state.authenticated:
        if st.sidebar.button("Logout"):
            logout()
            st.success("You have been logged out successfully.")
            time.sleep(1)
            st.rerun()

def display_user_info():
    """Display current user information."""
    if st.session_state.authenticated:
        st.sidebar.write(f"Logged in as: **{st.session_state.username}**")
        st.sidebar.write(f"Role: **{config.ROLES[st.session_state.role]['name']}**")