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
    page_icon="📋",
    layout="wide",
    #initial_sidebar_state="expanded"
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
    st.sidebar.title(config.APP_NAME)
    
    # Dark/Light mode toggle
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    
    dark_mode = st.sidebar.checkbox("Dark Mode", value=st.session_state.dark_mode)
    
    if dark_mode != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode
        
    
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
            dashboard.render_dashboard()
        
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
            user_data.append({
                'ID': user['id'],
                'Username': user['username'],
                'Role': config.ROLES[user['role']]['name'],
                'Last Login': user['last_login'] or "Never"
            })
        
        st.dataframe(user_data)
    else:
        st.info("No users found.")
    
    # Create new user
    st.header("Create New User")
    
    with st.form("new_user_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        role_options = {role_info['name']: role for role, role_info in config.ROLES.items()}
        selected_role_name = st.selectbox("Role", list(role_options.keys()))
        selected_role = role_options[selected_role_name]
        
        st.info(f"This role has the following permissions: {', '.join(config.ROLES[selected_role]['permissions'])}")
        
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
            user_id = db.create_user(username, password_hash, selected_role)
            
            if user_id:
                st.success(f"User '{username}' created successfully with role '{selected_role_name}'!")
                time.sleep(1)
                 
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
                 
            
            if st.session_state.get('confirm_delete_user_cancel', False):
                if 'confirm_delete_user' in st.session_state:
                    del st.session_state.confirm_delete_user
                 
    else:
        st.info("There are no other users besides yourself that can be deleted.")

if __name__ == "__main__":
    main()