"""
On-site registration management functions for the Event Registration System.
"""
import streamlit as st
import pandas as pd
import time
from database import Database
import utils
import auth

@auth.requires_auth('manage_registration')
def render_registration():
    """Render the registration management page."""
    st.title("Registration Management")
    
    db = Database()
    events = db.get_all_events()
    
    if not events:
        st.warning("No events found. Please create an event first.")
        return
    
    # Event selection
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
    
    search_term = st.text_input("Search by name, college, phone, or email")
    
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
        
        participants_data.append({
            "ID": p['id'],
            "Name": p['name'],
            "College": p['college'] or "-",
            "Phone": p['phone'] or "-",
            "Email": p['email'] or "-",
            "Group": p['group_name'] or "-",
            "Status": checked_in_status,
            "Check-in Time": check_in_time
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
        participant_options = {f"{p['id']}: {p['name']}": p['id'] for p in participants}
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
    
    if st.button("Confirm Check-in"):
        success = db.check_in_participant(participant['id'], st.session_state.user_id)
        
        if success:
            st.success(f"✅ {participant['name']} has been checked in successfully!")
            time.sleep(1)
             
        else:
            st.error("Failed to check in participant. They may already be checked in.")

def perform_undo_check_in(participant, db):
    """Undo a check-in for a participant."""
    st.subheader(f"Undo check-in: {participant['name']}")
    
    st.warning("This will remove the check-in record for this participant.")
    
    if st.button("Confirm Undo Check-in"):
        success = db.undo_check_in(participant['id'], st.session_state.user_id)
        
        if success:
            st.success(f"✅ Check-in has been undone for {participant['name']}.")
            time.sleep(1)
             
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
             
        else:
            st.error("Failed to update participant details.")

def view_participant_history(participant, db):
    """View the modification history for a participant."""
    st.subheader(f"History for: {participant['name']}")
    
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