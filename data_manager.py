"""
Data upload and management functions for the Event Registration System.
"""
import streamlit as st
import pandas as pd
import io
import os
import time
import datetime
from database import Database
import utils
import auth

@auth.requires_auth('upload_data')
def render_data_manager():
    """Render the data manager page."""
    st.title("Data Management")
    
    tabs = st.tabs(["Upload Registrations", "Manage Events", "Participant Manager", "Data Backup"])
    
    with tabs[0]:
        render_upload_section()
    
    with tabs[1]:
        render_event_management()
    
    with tabs[2]:
        render_registrations()
    
    with tabs[3]:
        render_backup_section()

def render_upload_section():
    """Render the registration data upload section."""
    st.header("Upload Registration Data")
    
    db = Database()
    events = db.get_all_events()
    
    if not events:
        st.warning("No events found. Please create an event first.")
        return
    
    # Download template button
    template_path = utils.create_registration_template()
    st.markdown(utils.get_download_link(template_path, "📥 Download Registration Template"), unsafe_allow_html=True)
    
    st.markdown("### Upload Registration Data")
    
    upload_file = st.file_uploader("Choose an Excel or CSV file", type=["xlsx", "csv"])
    
    if upload_file:
        try:
            if upload_file.name.endswith('.csv'):
                df = pd.read_csv(upload_file)
            else:
                df = pd.read_excel(upload_file)
            
            st.success(f"File uploaded successfully! Found {len(df)} records.")
            
            # Validate the data
            is_valid, errors, warnings = utils.validate_uploaded_data(df, events)
            
            if not is_valid:
                st.error("The uploaded data contains errors that must be fixed:")
                for error in errors:
                    st.markdown(f"- {error}")
                return
            
            if warnings:
                st.warning("The uploaded data contains some warnings:")
                for warning in warnings:
                    st.markdown(f"- {warning}")
            
            # Preview the data
            st.subheader("Data Preview(Verify & Edit the data before confirming)")
            #st.dataframe(df)
            
            # Allow for edits
            #if st.checkbox("Edit data before submission"):
            edited_df = st.data_editor(df)
            df = edited_df
            
            # Confirm upload
            if st.button("Confirm Upload"):
                loading = utils.show_loading_spinner("Processing your data...")
                
                try:
                    # Prepare data for database
                    data_for_db = utils.prepare_data_for_db(df)
                    st.write(data_for_db)
                    # Insert into database
                    db.bulk_add_participants(data_for_db)
                    
                    loading.success(f"Successfully added {len(data_for_db)} participants!")
                    time.sleep(2)
                     
                except Exception as e:
                    loading.error(f"Error ps uploading data: {str(e)}")
        
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

def render_event_management():
    """Render the event management section."""
    st.header("Manage Events")
    
    db = Database()
    
    # Current events
    st.subheader("Current Events")
    events = db.get_all_events()
    
    if events:
        # Convert to DataFrame for better display
        events_df = pd.DataFrame([dict(e) for e in events])
        events_df['date'] = pd.to_datetime(events_df['date']).dt.strftime('%Y-%m-%d')
        events_df = events_df[['id', 'name', 'date', 'location', 'description']]
        
        st.dataframe(events_df)
        
        # Event actions
        st.subheader("Event Actions")
        
        # Select event for actions
        event_options = {f"{e['id']}: {e['name']}": e['id'] for e in events}
        selected_event_key = st.selectbox("Select an event", list(event_options.keys()))
        selected_event_id = event_options[selected_event_key]
        
        # Get selected event details
        selected_event = next((e for e in events if e['id'] == selected_event_id), None)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Edit event
            if st.button("Edit Event"):
                st.session_state.edit_event_id = selected_event_id
                st.session_state.edit_event_name = selected_event['name']
                st.session_state.edit_event_description = selected_event['description'] or ""
                st.session_state.edit_event_date = selected_event['date']
                st.session_state.edit_event_location = selected_event['location'] or ""
        
        with col2:
            # Delete event
            if st.button("Delete Event"):
                if 'confirm_delete_event' not in st.session_state:
                    st.session_state.confirm_delete_event = selected_event_id
                    st.warning(f"Are you sure you want to delete '{selected_event['name']}'? This will also delete all participants registered for this event.")
                    st.button("Yes, Delete", key="confirm_delete_yes")
                    st.button("Cancel", key="confirm_delete_cancel")
        
        # Handle confirmation
        if 'confirm_delete_event' in st.session_state:
            if st.session_state.get('confirm_delete_yes', False):
                db.delete_event(st.session_state.confirm_delete_event)
                st.success("Event deleted successfully!")
                if 'confirm_delete_event' in st.session_state:
                    del st.session_state.confirm_delete_event
                time.sleep(1)
                 
            
            if st.session_state.get('confirm_delete_cancel', False):
                if 'confirm_delete_event' in st.session_state:
                    del st.session_state.confirm_delete_event
                 
        
        # Edit event form
        if 'edit_event_id' in st.session_state:
            st.subheader(f"Edit Event: {st.session_state.edit_event_name}")
            
            with st.form("edit_event_form"):
                name = st.text_input("Event Name", value=st.session_state.edit_event_name)
                description = st.text_area("Description", value=st.session_state.edit_event_description)
                date = st.date_input("Event Date", value=pd.to_datetime(st.session_state.edit_event_date))
                location = st.text_input("Location", value=st.session_state.edit_event_location)
                
                col1, col2 = st.columns(2)
                with col1:
                    update_button = st.form_submit_button("Update Event")
                with col2:
                    cancel_button = st.form_submit_button("Cancel")
            
            if update_button:
                db.update_event(
                    st.session_state.edit_event_id,
                    name,
                    description,
                    date.strftime('%Y-%m-%d'),
                    location
                )
                st.success("Event updated successfully!")
                
                # Clear session state
                if 'edit_event_id' in st.session_state:
                    del st.session_state.edit_event_id
                    del st.session_state.edit_event_name
                    del st.session_state.edit_event_description
                    del st.session_state.edit_event_date
                    del st.session_state.edit_event_location
                
                time.sleep(1)
                 
            
            if cancel_button:
                # Clear session state
                if 'edit_event_id' in st.session_state:
                    del st.session_state.edit_event_id
                    del st.session_state.edit_event_name
                    del st.session_state.edit_event_description
                    del st.session_state.edit_event_date
                    del st.session_state.edit_event_location
                
                 
    
    else:
        st.info("No events found. Create a new event below.")
    
    # Create new event
    st.subheader("Create New Event")
    
    with st.form("new_event_form"):
        name = st.text_input("Event Name")
        description = st.text_area("Description")
        date = st.date_input("Event Date")
        location = st.text_input("Location")
        
        submit_button = st.form_submit_button("Create Event")
    
    if submit_button:
        if not name:
            st.error("Event name is required.")
            return
        
        db.create_event(
            name,
            description,
            date.strftime('%Y-%m-%d'),
            location,
            st.session_state.user_id
        )
        
        st.success(f"Event '{name}' created successfully!")
        time.sleep(1)
         

def render_backup_section():
    """Render the data backup and restore section."""
    st.header("Data Backup & Restore")
    
    db = Database()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Create Backup")
        
        # Add custom filename option
        default_filename = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        custom_filename = st.text_input("Backup Filename (optional)", value=default_filename)
        
        if st.button("Create New Backup"):
            backup_path = db.create_backup(custom_filename)
            if backup_path:
                st.success(f"Backup created successfully at: {os.path.basename(backup_path)}")
            else:
                st.error("Failed to create backup.")
    
    with col2:
        # Export data section
        st.subheader("Export Data")
        
        export_options = ["All Participants", "By Event"]
        export_choice = st.radio("Export options:", export_options,key="export_options")
        
        if export_choice == "By Event":
            events = db.get_all_events()
            if events:
                event_options = {f"{e['id']}: {e['name']}": e['id'] for e in events}
                selected_event_key = st.selectbox("Select event to export", list(event_options.keys()))
                selected_event_id = event_options[selected_event_key]
                
                if st.button("Export Participants"):
                    participants_df = db.export_participants_data(selected_event_id)
                    st.success(f"Found {len(participants_df)} participants.")
                    
                    # Download links
                    st.markdown(utils.export_to_csv(participants_df, f"participants_event_{selected_event_id}.csv"), unsafe_allow_html=True)
                    st.markdown(utils.export_to_excel(participants_df, f"participants_event_{selected_event_id}.xlsx"), unsafe_allow_html=True)
            else:
                st.info("No events found.")
        else:
            if st.button("Export All Participants"):
                participants_df = db.export_participants_data()
                st.success(f"Found {len(participants_df)} participants.")
                
                # Download links
                st.markdown(utils.export_to_csv(participants_df, "all_participants.csv"), unsafe_allow_html=True)
                st.markdown(utils.export_to_excel(participants_df, "all_participants.xlsx"), unsafe_allow_html=True)
    
    # Backup history and restore
    st.subheader("Backup History")
    backups = db.list_backups()
    
    if backups:
        backup_df = pd.DataFrame([
            {
                'Filename': b['filename'],
                'Created': b['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                'Size (KB)': round(b['size'] / 1024, 2)
            } for b in backups
        ])
        
        st.dataframe(backup_df)
        
        # Restore from backup
        st.subheader("Restore from Backup")
        
        backup_options = {b['filename']: b['path'] for b in backups}
        selected_backup = st.selectbox("Select backup to restore", list(backup_options.keys()))
        
        if st.button("Restore Database"):
            # Confirm restore
            if 'confirm_restore' not in st.session_state:
                st.session_state.confirm_restore = selected_backup
                st.warning("⚠️ WARNING: Restoring from a backup will overwrite your current database. This action cannot be undone.")
                st.warning("Are you sure you want to continue?")
                st.button("Yes, Restore", key="confirm_restore_yes")
                st.button("Cancel", key="confirm_restore_cancel")
        
        # Handle confirmation
        if 'confirm_restore' in st.session_state:
            if st.session_state.get('confirm_restore_yes', False):
                backup_path = backup_options[st.session_state.confirm_restore]
                success = db.restore_backup(backup_path)
                
                if success:
                    st.success("Database restored successfully!")
                else:
                    st.error("Failed to restore database.")
                
                if 'confirm_restore' in st.session_state:
                    del st.session_state.confirm_restore
                
                time.sleep(1)
                st.rerun()
            
            if st.session_state.get('confirm_restore_cancel', False):
                if 'confirm_restore' in st.session_state:
                    del st.session_state.confirm_restore
                st.rerun()
    else:
        st.info("No backups found.")
    
   
def render_registrations():
    db = Database()
    # Registration management section
    st.header("Participant Management")
    
    # Event filter
    events = db.get_all_events()
    
    event_options = {"All Events": None}
    event_options.update({f"{e['id']}: {e['name']}": e['id'] for e in events})
    
    selected_event_key = st.selectbox("Filter by Event", list(event_options.keys()), key="registration_filter")
    selected_event_id = event_options[selected_event_key]
    
    # Search filter
    
    participants = db.get_all_participants(selected_event_id)
    
    if participants:
        # Convert to DataFrame for display and editing
        participants_data = []
        for p in participants:
            # Format the checked-in status as text
            checked_in_status = "✅ Checked In" if p['checked_in'] else "❌ Not Checked In"
            
            participants_data.append({
                "ID": p['id'],
                "Name": p['name'],
                "Email": p['email'] or "",
                "Phone": p['phone'] or "",
                "College": p['college'] or "",
                "Group": p['group_name'] or "",
                "Event": p['event_name'],
                "Checked In": checked_in_status,
                "Check-in Time": p['check_in_time'] or ""
            })
        
        df = pd.DataFrame(participants_data)
        
        # Display in a dataframe with editing capability
        st.write(f"### Participants ({len(df)})")
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn(
                    "ID",
                    help="Participant ID",
                    disabled=True,
                    width="small"
                ),
                "Name": st.column_config.TextColumn(
                    "Name",
                    help="Participant name",
                    width="medium",
                    required=True
                ),
                "Email": st.column_config.TextColumn(
                    "Email",
                    help="Email address",
                    width="medium"
                ),
                "Phone": st.column_config.TextColumn(
                    "Phone",
                    help="Phone number",
                    width="medium"
                ),
                "College": st.column_config.TextColumn(
                    "College",
                    help="College/Institution",
                    width="medium"
                ),
                "Group": st.column_config.TextColumn(
                    "Group",
                    help="Group/Team name",
                    width="medium"
                ),
                "Event": st.column_config.TextColumn(
                    "Event",
                    help="Event name",
                    width="medium",
                    disabled=True
                ),
                "Checked In": st.column_config.TextColumn(
                    "Checked In Status",
                    help="Check-in status",
                    width="small",
                    disabled=True
                ),
                "Check-in Time": st.column_config.TextColumn(
                    "Check-in Time",
                    help="Time of check-in",
                    width="medium",
                    disabled=True
                )
            }
        )
        
        # Check if there are changes and save them
        if not df.equals(edited_df):
            # Detect which rows were changed
            changed_rows = []
            
            for index, row in edited_df.iterrows():
                original_row = df.iloc[index]
                # Only check for changes in editable fields
                if (row["Name"] != original_row["Name"] or
                    row["Email"] != original_row["Email"] or
                    row["Phone"] != original_row["Phone"] or
                    row["College"] != original_row["College"] or
                    row["Group"] != original_row["Group"]):
                    
                    changed_rows.append({
                        "id": row["ID"],
                        "name": row["Name"],
                        "email": row["Email"],
                        "phone": row["Phone"],
                        "college": row["College"],
                        "group": row["Group"]
                    })
            
            if changed_rows and st.button("Save Changes"):
                success_count = 0
                for row in changed_rows:
                    # Find the original participant to get both event_id and checked_in status
                    original_participant = next((p for p in participants if p['id'] == row['id']), None)
                    
                    if original_participant:
                        # Get event_id and checked_in status from original data
                        event_id = original_participant['event_id']
                        checked_in = original_participant['checked_in']
                        
                        success = db.update_participant_full(
                            row['id'],
                            row['name'],
                            row['email'],
                            row['phone'],
                            row['college'],
                            row['group'],
                            event_id,
                            checked_in,  # Use the original checked_in status
                            st.session_state.user_id
                        )
                        
                        if success:
                            success_count += 1
                
                if success_count > 0:
                    st.success(f"Successfully updated {success_count} participants.")
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("No participants found matching your criteria.")
        