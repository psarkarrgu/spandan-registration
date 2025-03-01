"""
Main application entry point for the Event Registration System.
"""
import streamlit as st
import os
import time
from database import Database
import auth
import utils
import data_manager
import registration
import dashboard
import config

# Set page config
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon=config.APP_ICON,
    layout="wide",
    
)

# Apply custom CSS
utils.apply_custom_css()

def main():
    """Main function to run the Streamlit app."""
    # Initialize authentication state
    auth.init_auth()
    
    # Create initial admin account if no users exist
    auth.create_initial_admin()
    
    # Sidebar
    st.sidebar.image(config.EVENT_ICON,width=250)
    st.sidebar.title(config.APP_NAME)
    st.sidebar.markdown("#### Developer👨🏻‍💻[Pranay Sarkar](https://www.linkedin.com/in/pranay-sarkar/)")
    
    
    # Dark/Light mode toggle
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    
    dark_mode = False
    
    if dark_mode != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode
        st.rerun()
    
    utils.set_theme(dark_mode)
    
    # Display user info and logout button
    auth.display_user_info()
    auth.display_logout_button()
    
    # Navigation
    if auth.is_viewer():
        # For viewers or unauthenticated users, show only the dashboard
        dashboard.render_dashboard()
    else:
        # For authenticated users with roles
        nav_options = []
        
        if 'view_dashboard' in st.session_state.permissions:
            nav_options.append("Dashboard")
        
        if 'manage_registration' in st.session_state.permissions:
            nav_options.append("Registration")
        
        if 'upload_data' in st.session_state.permissions:
            nav_options.append("Data Management")
        
        if 'manage_users' in st.session_state.permissions:
            nav_options.append("User Management")
        
        if not nav_options:
            st.error("You don't have permissions to access any module.")
            return
        
        nav_selection = st.sidebar.radio("Navigation", nav_options)
        
        if nav_selection == "Dashboard":
            try:
                dashboard.render_dashboard()
            except AttributeError:
                # Fallback in case module or function can't be found
                st.error("Dashboard module not found. Please check your installation.")
                st.info("Try renaming dashboard-py-final.py to dashboard.py if you have both files.")
                st.write("You can also copy the dashboard code from the correct file to dashboard.py.")
                st.write("Technical error: module 'dashboard' has no attribute 'render_dashboard'")
        
        elif nav_selection == "Registration":
            registration.render_registration()
        
        elif nav_selection == "Data Management":
            data_manager.render_data_manager()
        
        elif nav_selection == "User Management":
            render_user_management()

def render_user_management():
    """Render the user management interface."""
    st.title("User Management")
    
    db = Database()
    
    # Current users
    st.header("Current Users")
    users = db.get_all_users()
    
    if users:
        user_data = []
        for user in users:
            # Get event name if assigned
            event_name = "All Events"
            if user['assigned_event_id']:
                event = db.get_event(user['assigned_event_id'])
                if event:
                    event_name = event['name']
            
            user_data.append({
                'ID': user['id'],
                'Username': user['username'],
                'Role': config.ROLES[user['role']]['name'],
                'Assigned Event': event_name if user['role'] == 'viewer' else "N/A",
                'Last Login': user['last_login'] or "Never"
            })
        
        st.dataframe(user_data)
    else:
        st.info("No users found.")
    
    # Create new user
    st.header("Create New User")
    
    # Initialize session state values for the form
    if 'new_user_role' not in st.session_state:
        st.session_state.new_user_role = 'viewer'  # Default role
    
    # Role selection outside the form for dynamic UI
    role_options = {role_info['name']: role for role, role_info in config.ROLES.items()}
    selected_role_name = st.selectbox(
        "Role", 
        list(role_options.keys()),
        key="role_selector"
    )
    selected_role = role_options[selected_role_name]
    
    # Check if role changed and update session state
    if st.session_state.new_user_role != selected_role:
        st.session_state.new_user_role = selected_role
    
    # Show event assignment option outside the form
    assigned_event_id = None
    if selected_role == 'viewer':
        st.write("**Assign to Specific Event:**")
        events = db.get_all_events()
        
        if events:
            event_options = {f"{e['id']}: {e['name']}": e['id'] for e in events}
            event_options["All Events"] = None
            selected_event_key = st.selectbox("Select Event Access", list(event_options.keys()))
            assigned_event_id = event_options[selected_event_key]
            
            if assigned_event_id:
                st.info(f"This viewer will only have access to the selected event.")
            else:
                st.info(f"This viewer will have access to all events.")
        else:
            st.warning("No events found. The viewer will have access to all future events.")
    
    st.info(f"This role has the following permissions: {', '.join(config.ROLES[selected_role]['permissions'])}")
    
    # User creation form with username and password
    with st.form("new_user_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        # Add hidden field to store the role and event
        st.text_input("Selected Role", selected_role, disabled=True, label_visibility="hidden", key="hidden_role")
        
        submit = st.form_submit_button("Create User")
    
    if submit:
        if not username or not password:
            st.error("Username and password are required.")
        elif password != confirm_password:
            st.error("Passwords do not match.")
        else:
            # Hash password
            password_hash = auth.hash_password(password)
            
            # Try to create user
            user_id = db.create_user(username, password_hash, selected_role, assigned_event_id)
            
            if user_id:
                st.success(f"User '{username}' created successfully with role '{selected_role_name}'!")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Failed to create user. Username '{username}' may already exist.")
    
    # Delete user
    st.header("Delete User")
    
    # Cannot delete yourself
    users_except_current = [u for u in users if u['id'] != st.session_state.user_id]
    
    if users_except_current:
        user_options = {f"{u['id']}: {u['username']} ({config.ROLES[u['role']]['name']})": u['id'] for u in users_except_current}
        selected_user_key = st.selectbox("Select user to delete", list(user_options.keys()))
        selected_user_id = user_options[selected_user_key]
        
        if st.button("Delete User"):
            # Confirm deletion
            if 'confirm_delete_user' not in st.session_state:
                st.session_state.confirm_delete_user = selected_user_id
                st.warning(f"Are you sure you want to delete this user? This action cannot be undone.")
                st.button("Yes, Delete", key="confirm_delete_user_yes")
                st.button("Cancel", key="confirm_delete_user_cancel")
        
        # Handle confirmation
        if 'confirm_delete_user' in st.session_state:
            if st.session_state.get('confirm_delete_user_yes', False):
                db.delete_user(st.session_state.confirm_delete_user)
                st.success("User deleted successfully!")
                
                if 'confirm_delete_user' in st.session_state:
                    del st.session_state.confirm_delete_user
                
                time.sleep(1)
                st.rerun()
            
            if st.session_state.get('confirm_delete_user_cancel', False):
                if 'confirm_delete_user' in st.session_state:
                    del st.session_state.confirm_delete_user
                st.rerun()
    else:
        st.info("There are no other users besides yourself that can be deleted.")

if __name__ == "__main__":
    main()