"""
Dashboard and reporting functions for the Event Registration System.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from database import Database
import utils
import auth
import config

@auth.requires_auth('view_dashboard')
def render_dashboard():
    """Render the real-time dashboard."""
    st.title("Event Dashboard")
    
    db = Database()
    
    # Dashboard filter options
    st.sidebar.header("Dashboard Filters")
    
    # Event filter
    events = db.get_all_events()
    
    if not events:
        st.warning("No events found. Please create an event first.")
        return
    
    # If user is a viewer with an assigned event, restrict view to that event only
    if st.session_state.role == 'viewer' and st.session_state.assigned_event_id:
        assigned_event = db.get_event(st.session_state.assigned_event_id)
        if assigned_event:
            event_id = assigned_event['id']
            event_name = assigned_event['name']
            
            st.sidebar.info(f"You have access to view: **{event_name}**")
            
            # Render the dashboard components with the assigned event
            render_overview_section(db, event_id, event_name)
            render_attendance_section(db, event_id, event_name)
            #render_college_breakdown(db, event_id, event_name)
            #render_check_in_timeline(db, event_id, event_name)
            render_export_options(db, event_id, event_name)
            return
    
    # For users with access to all events
    view_options = ["All Events"] + [f"{e['id']}: {e['name']}" for e in events]
    selected_view = st.sidebar.selectbox("Select View", view_options)
    
    
    
    
    # Filter data based on selection
    if selected_view == "All Events":
        event_id = None
        event_name = "All Events"
    else:
        event_id = int(selected_view.split(":")[0])
        event_name = selected_view.split(":", 1)[1].strip()
    
    # Render the dashboard components
    render_overview_section(db, event_id, event_name)
    render_attendance_section(db, event_id, event_name)
    #render_college_breakdown(db, event_id, event_name)
    render_check_in_timeline(db, event_id, event_name)
    
    # Export options
    render_export_options(db, event_id, event_name)

def render_overview_section(db, event_id, event_name):
    """Render the overview section with key metrics."""
    st.header(f"Overview: {event_name}")
    
    # Get statistics
    stats = db.get_participant_stats(event_id)
    
    if not stats:
        st.info("No data available.")
        return
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Registered", stats['total'])
    
    with col2:
        st.metric("Checked In", stats['checked_in'])
    
    with col3:
        # Calculate percentage if there are registrations
        if stats['total'] > 0:
            check_in_percent = round((stats['checked_in'] / stats['total']) * 100, 1)
        else:
            check_in_percent = 0
        
        st.metric("Check-in Rate", f"{check_in_percent}%")
    
    # Create a simple gauge chart for check-in percentage
    if stats['total'] > 0:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=check_in_percent,
            title={'text': "Check-in Percentage"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': config.PRIMARY_COLOR if check_in_percent < 80 else config.SUCCESS_COLOR},
                'steps': [
                    {'range': [0, 50], 'color': "#ffcccb"},
                    {'range': [50, 80], 'color': "#ffffcc"},
                    {'range': [80, 100], 'color': "#ccffcc"},
                ]
            }
        ))
        
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)

def render_attendance_section(db, event_id, event_name):
    """Render the attendance breakdown section."""
    st.header("Attendance Breakdown")
    
    if event_id is None:
        # Show event-wise breakdown
        events_stats = db.get_event_stats()
        
        if not events_stats:
            st.info("No event data available.")
            return
        
        # Convert to DataFrame for plotting
        data = []
        
        for e in events_stats:
            if e['total_participants'] > 0:  # Only include events with participants
                data.append({
                    'Event': e['name'],
                    'Registered': e['total_participants'],
                    'Checked In': e['checked_in'],
                    'Not Checked In': e['total_participants'] - e['checked_in']
                })
        
        if not data:
            st.info("No participant data available for any events.")
            return
        
        df = pd.DataFrame(data)
        
        # Create stacked bar chart
        fig = px.bar(
            df,
            x='Event',
            y=['Checked In', 'Not Checked In'],
            title='Attendance by Event',
            barmode='stack',
            color_discrete_map={
                'Checked In': config.SUCCESS_COLOR,
                'Not Checked In': config.WARNING_COLOR
            }
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    else:
        # Show status breakdown for single event
        
        # Add participant status table
        show_participant_status_table(db, event_id, event_name)

def render_college_breakdown(db, event_id, event_name):
    """Render the college-wise breakdown section."""
    st.header("College Breakdown")
    
    college_stats = db.get_college_stats(event_id)
    
    if not college_stats:
        st.info("No college data available.")
        return
    
    # Convert to DataFrame for plotting
    data = []
    
    for c in college_stats:
        college_name = c['college'] or "Not Specified"
        data.append({
            'College': college_name,
            'Registered': c['total'],
            'Checked In': c['checked_in'],
            'Not Checked In': c['total'] - c['checked_in']
        })
    
    df = pd.DataFrame(data)
    
    # Sort by total registrations
    df = df.sort_values('Registered', ascending=False)
    
    # Limit to top 10 colleges for better visualization
    if len(df) > 10:
        top_df = df.head(10)
        others_df = df.iloc[10:].sum().to_frame().T
        others_df['College'] = 'Others'
        df = pd.concat([top_df, others_df])
    
    # Create horizontal stacked bar chart
    fig = px.bar(
        df,
        y='College',
        x=['Checked In', 'Not Checked In'],
        title='Participation by College',
        barmode='stack',
        orientation='h',
        color_discrete_map={
            'Checked In': config.SUCCESS_COLOR,
            'Not Checked In': config.WARNING_COLOR
        }
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_check_in_timeline(db, event_id, event_name):
    """Render the check-in timeline chart."""
    st.header("Check-in Timeline")
    
    # Date selection
    today = datetime.datetime.now().date()
    selected_date = today 

    
    # Get check-in data
    timeline_data = db.get_check_in_timeline(event_id, selected_date.strftime("%Y-%m-%d"))
    
    if not timeline_data:
        st.info("No check-in data available for today.")
        return
    
    # Convert to DataFrame for plotting
    data = []
    
    # Fill in all hours even if no check-ins
    hour_data = {h['hour']: h['count'] for h in timeline_data}
    
    for hour in range(24):
        hour_str = str(hour).zfill(2)
        count = hour_data.get(hour_str, 0)
        
        data.append({
            'Hour': f"{hour_str}:00",
            'Check-ins': count
        })
    
    df = pd.DataFrame(data)
    
    # Create bar chart
    fig = px.bar(
        df,
        x='Hour',
        y='Check-ins',
        title=f'Check-in Timeline for {selected_date.strftime("%d %b %Y")}',
        color='Check-ins',
        color_continuous_scale=['lightblue', 'darkblue']
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_participant_status_table(db, event_id, event_name):
    """Display a table of participants with their check-in status."""
    st.subheader("Participant Status List")
    
    # Get all participants for the event
    participants = db.get_participants_by_event(event_id)
    
    if not participants:
        st.info("No participants found for this event.")
        return
    
    # Create a DataFrame for the table
    participant_data = []
    
    for p in participants:
        check_in_status = "✅ Checked In" if p['checked_in'] else "❌ Not Checked In"
        
        # Create clickable phone number
        phone_display = p['phone'] if p['phone'] else "-"
        if p['phone']:
            # Create a clickable link that initiates a call
            phone_display = f"<a href='tel:{p['phone']}'>{p['phone']}</a>"
        
        participant_data.append({
            "Name": p['name'],
            "College": p['college'] or "-",
            "Phone": phone_display,
            "Status": check_in_status
        })
    
    # Convert to DataFrame
    df = pd.DataFrame(participant_data)
    
    # Show search box for filtering participants
    search_term = st.text_input("Search participants by name or college", key="dashboard_participant_search")
    
    if search_term:
        # Filter the DataFrame
        filtered_df = df[
            df['Name'].str.contains(search_term, case=False, na=False) | 
            df['College'].str.contains(search_term, case=False, na=False)
        ]
        
        if len(filtered_df) > 0:
            # Display the filtered results
            st.write(f"Found {len(filtered_df)} matching participants")
            
            # Convert DataFrame to HTML with clickable phone numbers
            html = filtered_df.to_html(escape=False, index=False)
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.info("No matching participants found.")
    else:
        # Display all participants
        # Convert DataFrame to HTML with clickable phone numbers
        html = df.to_html(escape=False, index=False)
        st.markdown(html, unsafe_allow_html=True)
    
   

def render_export_options(db, event_id, event_name):
    """Render export options for the dashboard."""
    st.header("Export Reports")
    
    export_type = st.selectbox(
        "Select Export Type",
        ["Participant List", "Check-in Status"]
    )
    
    if export_type == "Participant List":
        # Export participant list
        if event_id:
            participants_df = db.export_participants_data(event_id)
            filename_prefix = f"participants_{event_name.replace(' ', '_')}"
        else:
            participants_df = db.export_participants_data()
            filename_prefix = "all_participants"
        
        if len(participants_df) > 0:
            st.success(f"Found {len(participants_df)} participants.")
            
            # Download links
            st.markdown(utils.export_to_csv(participants_df, f"{filename_prefix}.csv"), unsafe_allow_html=True)
            st.markdown(utils.export_to_excel(participants_df, f"{filename_prefix}.xlsx"), unsafe_allow_html=True)
        else:
            st.info("No participant data available to export.")
    
    elif export_type == "Check-in Status":
        # Export check-in status
        if event_id:
            participants = db.get_participants_by_event(event_id)
            filename_prefix = f"checkin_status_{event_name.replace(' ', '_')}"
        else:
            # Get all participants across all events
            participants = []
            for e in db.get_all_events():
                participants.extend(db.get_participants_by_event(e['id']))
            
            filename_prefix = "all_checkin_status"
        
        if participants:
            # Convert to DataFrame
            data = []
            
            for p in participants:
                event_info = db.get_event(p['event_id'])
                event_name = event_info['name'] if event_info else "Unknown Event"
                
                data.append({
                    'Name': p['name'],
                    'Email': p['email'],
                    'Phone': p['phone'],
                    'College': p['college'],
                    'Group': p['group_name'],
                    'Event': event_name,
                    'Status': "Checked In" if p['checked_in'] else "Not Checked In",
                    'Check-in Time': p['check_in_time'] or ""
                })
            
            df = pd.DataFrame(data)
            
            st.success(f"Found {len(df)} records.")
            
            # Download links
            st.markdown(utils.export_to_csv(df, f"{filename_prefix}.csv"), unsafe_allow_html=True)
            st.markdown(utils.export_to_excel(df, f"{filename_prefix}.xlsx"), unsafe_allow_html=True)
        else:
            st.info("No data available to export.")
    
    elif export_type == "College Statistics":
        # Export college statistics
        college_stats = db.get_college_stats(event_id)
        
        if college_stats:
            # Convert to DataFrame
            data = []
            
            for c in college_stats:
                college_name = c['college'] or "Not Specified"
                data.append({
                    'College': college_name,
                    'Total Registered': c['total'],
                    'Checked In': c['checked_in'],
                    'Not Checked In': c['total'] - c['checked_in'],
                    'Check-in Percentage': round((c['checked_in'] / c['total']) * 100, 2) if c['total'] > 0 else 0
                })
            
            df = pd.DataFrame(data)
            
            if event_id:
                filename_prefix = f"college_stats_{event_name.replace(' ', '_')}"
            else:
                filename_prefix = "all_college_stats"
            
            st.success(f"Found statistics for {len(df)} colleges.")
            
            # Download links
            st.markdown(utils.export_to_csv(df, f"{filename_prefix}.csv"), unsafe_allow_html=True)
            st.markdown(utils.export_to_excel(df, f"{filename_prefix}.xlsx"), unsafe_allow_html=True)
        else:
            st.info("No college statistics available to export.")