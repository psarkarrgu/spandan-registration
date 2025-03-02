"""
On-site registration management functions for the Event Registration System.
"""
import streamlit as st
import pandas as pd
import time
import datetime
from database import Database
import utils
import auth

@auth.requires_auth('manage_registration')
def render_registration():
    """Render the registration management page."""
    st.title("Spandan Registration Management")
    
    db = Database()
    events = db.get_all_events()
    
    if not events:
        st.warning("No events found. Please create an event first.")
        return
    
    # Create tabs for different registration functions
    tabs = st.tabs(["Manage Check-ins", "On-spot Registration"])
    
    with tabs[0]:
        render_check_in(db, events)
    
    with tabs[1]:
        render_on_spot_registration(db, events)

def render_check_in(db, events):
    """Render the check-in management interface."""
    st.header("Event Selection")
    
    event_options = {f"{e['id']}: {e['name']}": e['id'] for e in events}
    selected_event_key = st.selectbox("Select Event", list(event_options.keys()))
    selected_event_id = event_options[selected_event_key]
    
    # Get selected event details for display
    selected_event = next((e for e in events if e['id'] == selected_event_id), None)
    
    if selected_event:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Event", selected_event['name'])
        
        with col2:
            st.metric("Date", pd.to_datetime(selected_event['date']).strftime('%Y-%m-%d'))
        
        with col3:
            st.metric("Location", selected_event['location'] or "Not specified")
    
    # Search participants
    st.subheader("Search Participants")
    
    search_term = st.text_input("Search by name, college, phone, email or Group")
    
    if search_term:
        participants = db.search_participants(search_term, selected_event_id)
        render_participant_list(participants, db, is_search_result=True)
    else:
        # Show all participants for the selected event
        participants = db.get_participants_by_event(selected_event_id)
        render_participant_list(participants, db, is_search_result=False)

def render_participant_list(participants, db, is_search_result=False):
    """Render the list of participants with actions."""
    if not participants:
        if is_search_result:
            st.info("No participants found matching your search.")
        else:
            st.info("No participants registered for this event yet.")
        return
    
    # Convert to DataFrame for better display
    participants_data = []
    
    for p in participants:
        checked_in_status = "✅ Checked In" if p['checked_in'] else "❌ Not Checked In"
        check_in_time = utils.format_check_in_time(p['check_in_time']) if p['checked_in'] else "-"
        
        # Add indicator for ID card photo
        has_photo = db.get_id_card_photo(p['id']) is not None
        photo_status = "📷" if has_photo else ""
        
        participants_data.append({
            "ID": p['id'],
            "Name": p['name'],
            "College": p['college'] or "-",
            "Phone": p['phone'] or "-",
            "Email": p['email'] or "-",
            "Group": p['group_name'] or "-",
            "Status": checked_in_status,
            "Check-in Time": check_in_time,
            "Photo": photo_status
        })
    
    participants_df = pd.DataFrame(participants_data)
    
    # Display participants table
    st.markdown(f"### Participants ({len(participants_df)})")
    st.dataframe(participants_df, use_container_width=True)
    
    # Actions for participants
    st.subheader("Participant Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Select participant for actions
        participant_options = {f"{p['id']}: {p['name']}" + (" 📷" if db.get_id_card_photo(p['id']) is not None else ""): p['id'] for p in participants}
        selected_participant_key = st.selectbox("Select a participant", list(participant_options.keys()))
        selected_participant_id = participant_options[selected_participant_key]
        
        # Get selected participant details
        selected_participant = next((p for p in participants if p['id'] == selected_participant_id), None)
    
    with col2:
        # Action selection
        action_options = ["Check-in", "Edit Details", "View History"]
        
        # If already checked in, change option to "Undo Check-in"
        if selected_participant and selected_participant['checked_in']:
            action_options[0] = "Undo Check-in"
        
        selected_action = st.selectbox("Select Action", action_options)
    
    # Display ID photo if available (before the action)
    
    
    # Perform selected action
    if selected_action == "Check-in" and selected_participant:
        perform_check_in(selected_participant, db)
    
    elif selected_action == "Undo Check-in" and selected_participant:
        perform_undo_check_in(selected_participant, db)
    
    elif selected_action == "Edit Details" and selected_participant:
        perform_edit_participant(selected_participant, db)
    
    elif selected_action == "View History" and selected_participant:
        view_participant_history(selected_participant, db)

def perform_check_in(participant, db):
    """Check in a participant."""
    st.subheader(f"Check in: {participant['name']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**College:** {participant['college'] or 'Not specified'}")
        st.write(f"**Phone:** {participant['phone'] or 'Not specified'}")
    
    with col2:
        st.write(f"**Email:** {participant['email'] or 'Not specified'}")
        st.write(f"**Group:** {participant['group_name'] or 'Not specified'}")
    
    # Add ID card photo capture option
    capture_id_card = False
   
    
    
    # Confirm check-in button
    if st.button("Confirm Check-in"):
        if capture_id_card and not 'id_card_photo' in locals():
            st.warning("Please capture the ID card photo first or uncheck the 'Capture ID Card Photo' option.")
        else:
            # Get the photo bytes if available, otherwise None
            photo_data = id_card_photo if capture_id_card and 'id_card_photo' in locals() else None
            
            # Wrap database operation in try-except
            try:
                success = db.check_in_participant(participant['id'], st.session_state.user_id, photo_data)
                
                
            except Exception as e:
                st.error(f"Error during check-in: {str(e)} Try again")
                

def perform_undo_check_in(participant, db):
    """Undo a check-in for a participant."""
    st.subheader(f"Undo check-in: {participant['name']}")
    
    st.warning("This will remove the check-in record for this participant.")
    
    if st.button("Confirm Undo Check-in"):
        success = db.undo_check_in(participant['id'], st.session_state.user_id)
        
        if success:
            st.success(f"✅ Check-in has been undone for {participant['name']}.")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Failed to undo check-in.")

def perform_edit_participant(participant, db):
    """Edit participant details."""
    st.subheader(f"Edit Participant: {participant['name']}")
    
    with st.form("edit_participant_form"):
        name = st.text_input("Name", value=participant['name'])
        email = st.text_input("Email", value=participant['email'] or "")
        phone = st.text_input("Phone", value=participant['phone'] or "")
        college = st.text_input("College", value=participant['college'] or "")
        group_name = st.text_input("Group Name", value=participant['group_name'] or "")
        
        submit = st.form_submit_button("Update Details")
    
    if submit:
        if not name:
            st.error("Name is required.")
            return
        
        success = db.update_participant(
            participant['id'],
            name,
            email,
            phone,
            college,
            group_name,
            st.session_state.user_id
        )
        
        if success:
            st.success(f"✅ Details updated successfully for {name}!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Failed to update participant details.")

def view_participant_history(participant, db):
    """View the modification history for a participant."""
    st.subheader(f"History for: {participant['name']}")
    
    # Display ID card photo if available
    id_card_photo = db.get_id_card_photo(participant['id'])
    if id_card_photo:
        st.subheader("ID Card Photo")
        st.image(id_card_photo, caption="ID Card", width=300)
    
    history = db.get_data_modification_history(participant['id'])
    
    if not history:
        st.info("No modification history found for this participant.")
        return
    
    # Convert to DataFrame for better display
    history_data = []
    
    for h in history:
        history_data.append({
            "Field": h['field_name'],
            "Old Value": h['old_value'] or "-",
            "New Value": h['new_value'] or "-",
            "Modified By": h['modified_by_username'],
            "Modified At": utils.format_check_in_time(h['modified_at'])
        })
    
    history_df = pd.DataFrame(history_data)
    
    st.dataframe(history_df, use_container_width=True)

def render_on_spot_registration(db, events):
    """Render the on-spot registration interface."""
    st.header("On-spot Registration")
    st.info("Register new participants directly at the event.")
    
    # Event selection for on-spot registration
    event_options = {f"{e['id']}: {e['name']}": e['id'] for e in events}
    selected_event_key = st.selectbox("Select Event for Registration", list(event_options.keys()), key="onspot_event")
    selected_event_id = event_options[selected_event_key]
    
    # Get selected event details for display
    selected_event = next((e for e in events if e['id'] == selected_event_id), None)
    
    if selected_event:
        st.write(f"**Selected Event:** {selected_event['name']}")
        st.write(f"**Date:** {pd.to_datetime(selected_event['date']).strftime('%Y-%m-%d')}")
        st.write(f"**Location:** {selected_event['location'] or 'Not specified'}")
    
    # Registration form
    st.subheader("New Participant Registration")
    
    with st.form("onspot_registration_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Name*")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
        
        with col2:
            college = st.text_input("College")
            group_name = st.text_input("Group Name")
            auto_check_in = st.checkbox("Automatically check-in after registration", value=True)
        
        submit = st.form_submit_button("Register Participant")
    
    if submit:
        # Validate form
        if not name:
            st.error("Name is required.")
            return
        
        # Add participant to database
        participant_id = db.add_participant(
            name,
            email,
            phone,
            college,
            group_name,
            selected_event_id
        )
        
        if participant_id:
            st.success(f"✅ {name} has been registered successfully!")
            
            # Auto check-in if selected
            if auto_check_in:
                check_in_success = db.check_in_participant(participant_id, st.session_state.user_id)
                if check_in_success:
                    st.success(f"✅ {name} has been checked in automatically!")
                    
                    # Record check-in time for display
                    check_in_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.write(f"**Check-in Time:** {utils.format_check_in_time(check_in_time)}")
            
            # Clear form (using a session state trick)
            if 'form_submitted' not in st.session_state:
                st.session_state.form_submitted = True
                st.rerun()
            else:
                del st.session_state.form_submitted
        else:
            st.error("Failed to register participant. Please try again.")