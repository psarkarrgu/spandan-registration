"""
Utility functions for the Event Registration System.
"""
import streamlit as st
import pandas as pd
import io
import base64
import os
import datetime
import config
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
import plotly.express as px
import plotly.graph_objects as go
from database import Database

def create_registration_template():
    """Create and return a registration template Excel file."""
    if not os.path.exists(config.TEMPLATE_DIR):
        os.makedirs(config.TEMPLATE_DIR)
    
    template_path = os.path.join(config.TEMPLATE_DIR, "registration_template.xlsx")
    
    # Create a new workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Registration"
    
    # Define headers
    headers = ["Name", "Email", "Phone", "College", "Group Name", "Event ID"]
    
    # Add headers to the worksheet
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
    
    # Add some example data
    example_data = [
        ["John Doe", "john@example.com", "9876543210", "ABC College", "Team Alpha", "1"],
        ["Jane Smith", "jane@example.com", "8765432109", "XYZ University", "Team Alpha", "1"],
    ]
    
    for row_num, data_row in enumerate(example_data, 2):
        for col_num, value in enumerate(data_row, 1):
            ws.cell(row=row_num, column=col_num).value = value
    
    # Add a note about required fields
    ws.cell(row=len(example_data) + 3, column=1).value = "Required fields : Name , Event ID"
    ws.cell(row=len(example_data) + 4, column=1).value = "Note: Event ID refers to the ID of the event in the system."
    
    # Set column widths
    for col_num in range(1, len(headers) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = 20
    
    # Save the template
    wb.save(template_path)
    
    return template_path

def get_download_link(file_path, link_text):
    """Generate a download link for a file."""
    with open(file_path, 'rb') as f:
        data = f.read()
    
    b64 = base64.b64encode(data).decode()
    file_name = os.path.basename(file_path)
    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    href = f'<a href="data:{mime_type};base64,{b64}" download="{file_name}">{link_text}</a>'
    
    return href

def dataframe_to_excel(df):
    """Convert a pandas DataFrame to an Excel file in memory."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    
    return output.getvalue()

def validate_uploaded_data(df, events):
    """Validate uploaded registration data."""
    errors = []
    warnings = []
    
    # Check required columns
    required_columns = ['Name', 'Event ID']
    for col in required_columns:
        if col not in df.columns:
            pass
            #errors.append(f"Missing required column: {col}")
    
    # If there are column errors, return early
    if errors:
        return False, errors, warnings
    
    # Get valid event IDs
    valid_event_ids = [str(event['id']) for event in events]
    
    # Validate rows
    for idx, row in df.iterrows():
        # Check for missing required fields
        if pd.isna(row['Name']) or str(row['Name']).strip() == '':
            errors.append(f"Row {idx+2}: Missing required field 'Name'")
        
        if pd.isna(row['Event ID']) or str(row['Event ID']).strip() == '':
            errors.append(f"Row {idx+2}: Missing required field 'Event ID'")
        elif str(int(row['Event ID'])) not in valid_event_ids:
            errors.append(f"Row {idx+2}: Invalid Event ID '{row['Event ID']}'. Valid IDs are: {', '.join(valid_event_ids)}")
        
        # Check for valid email format if provided
        if 'Email' in df.columns and not pd.isna(row['Email']) and row['Email'].strip() != '':
            if '@' not in row['Email'] or '.' not in row['Email']:
                warnings.append(f"Row {idx+2}: Email '{row['Email']}' may not be valid")
        
        # Check for valid phone format if provided
        if 'Phone' in df.columns and not pd.isna(row['Phone']) and str(row['Phone']).strip() != '':
            phone_str = str(row['Phone']).strip()
            if not phone_str.isdigit() or len(phone_str) < 10:
                warnings.append(f"Row {idx+2}: Phone number '{phone_str}' may not be valid")
    
    return len(errors) == 0, errors, warnings

def prepare_data_for_db(df):
    """Prepare uploaded data for database insertion."""
    # Convert column names to lowercase
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    
    # Ensure event_id is an integer
    df['event_id'] = df['event_id'].astype(int)
    
    # Convert to list of dictionaries
    return df.to_dict('records')

def create_chart(chart_type, data, title, x_label, y_label):
    """Create a chart using Plotly."""
    if chart_type == 'bar':
        fig = px.bar(data, x=x_label, y=y_label, title=title)
    elif chart_type == 'pie':
        fig = px.pie(data, names=x_label, values=y_label, title=title)
    elif chart_type == 'line':
        fig = px.line(data, x=x_label, y=y_label, title=title)
    else:
        fig = go.Figure()
        fig.update_layout(title=title)
    
    fig.update_layout(
        title_font=dict(size=24),
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white"
    )
    
    return fig

def apply_custom_css():
    """Apply custom CSS to the Streamlit app."""
    css = """
    <style>
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #f0f2f6;
            border-radius: 4px 4px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #e0e0e0;
            border-bottom: 2px solid #1E88E5;
        }
        
        div[data-testid="stToolbar"] {
            visibility: hidden;
        }
        
        .success-card {
            background-color: #d7f7e1;
            padding: 20px;
            border-radius: 5px;
            border-left: 5px solid #4CAF50;
            margin-bottom: 20px;
        }
        
        .warning-card {
            background-color: #fff6e0;
            padding: 20px;
            border-radius: 5px;
            border-left: 5px solid #FF9800;
            margin-bottom: 20px;
        }
        
        .danger-card {
            background-color: #ffe0e0;
            padding: 20px;
            border-radius: 5px;
            border-left: 5px solid #F44336;
            margin-bottom: 20px;
        }
        
        .info-card {
            background-color: #e3f2fd;
            padding: 20px;
            border-radius: 5px;
            border-left: 5px solid #1E88E5;
            margin-bottom: 20px;
        }
        
        /* Status indicators */
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        
        .status-checked-in {
            background-color: #4CAF50;
        }
        
        .status-not-checked-in {
            background-color: #F44336;
        }
        
        /* Dark mode toggle */
        .dark-mode {
            background-color: #121212;
            color: #f0f2f6;
        }
        
        .dark-mode .stTabs [data-baseweb="tab"] {
            background-color: #2d2d2d;
            color: #f0f2f6;
        }
        
        .dark-mode .stTabs [aria-selected="true"] {
            background-color: #1a1a1a;
            border-bottom: 2px solid #90CAF9;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def set_theme(is_dark_mode):
    """Set the theme (light/dark) for the app."""
    if is_dark_mode:
        st.markdown('<body class="dark-mode">', unsafe_allow_html=True)
    else:
        st.markdown('<body>', unsafe_allow_html=True)

def export_to_csv(df, filename="export.csv"):
    """Generate a download link for a DataFrame as CSV."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV</a>'
    return href

def export_to_excel(df, filename="export.xlsx"):
    """Generate a download link for a DataFrame as Excel."""
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.close()
    
    b64 = base64.b64encode(output.getvalue()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">Download Excel</a>'
    return href

def format_check_in_time(time_str):
    """Format check-in time for display."""
    if not time_str:
        return "-"
    
    try:
        dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %b %Y, %I:%M %p")
    except:
        return time_str

def show_loading_spinner(text="Loading..."):
    """Display a loading spinner with text."""
    with st.spinner(text):
        placeholder = st.empty()
        return placeholder

def get_color_scale():
    """Get a nice color scale for charts."""
    return px.colors.sequential.Blues

def confirm_dialog(title, message, confirm_button_text="Confirm"):
    """Display a confirmation dialog."""
    return st.warning(f"{title}: {message}", icon="⚠️")