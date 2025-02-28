"""
Database setup and operations for the Event Registration System.
"""
import sqlite3
import os
import datetime
import pandas as pd
import json
import shutil
from pathlib import Path
import config

class Database:
    def __init__(self, db_path=config.DATABASE_PATH):
        self.db_path = db_path
        self.connection = None
        self.initialize_database()
    
    def get_connection(self):
        """Get a connection to the database."""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
        return self.connection
    
    def close_connection(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def initialize_database(self):
        """Initialize the database with required tables if they don't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            assigned_event_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            FOREIGN KEY (assigned_event_id) REFERENCES events (id)
        )
        ''')
        
        # Create Events table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            date DATE,
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
        ''')
        
        # Create Participants table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            college TEXT,
            group_name TEXT,
            event_id INTEGER,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checked_in INTEGER DEFAULT 0,
            check_in_time TIMESTAMP,
            id_card_photo BLOB,
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
        ''')
        
        # Create Data Modification History table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS data_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id INTEGER,
            field_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_by INTEGER,
            FOREIGN KEY (participant_id) REFERENCES participants (id),
            FOREIGN KEY (modified_by) REFERENCES users (id)
        )
        ''')
        
        conn.commit()
    
    def create_backup(self):
        """Create a backup of the database."""
        if not os.path.exists(self.db_path):
            return False
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(config.BACKUP_DIR, backup_filename)
        
        self.close_connection()  # Close connection before backup
        shutil.copy2(self.db_path, backup_path)
        return backup_path
    
    def list_backups(self):
        """List all available database backups."""
        if not os.path.exists(config.BACKUP_DIR):
            return []
            
        backups = []
        for file in os.listdir(config.BACKUP_DIR):
            if file.endswith('.db'):
                backup_path = os.path.join(config.BACKUP_DIR, file)
                backup_time = os.path.getctime(backup_path)
                backup_size = os.path.getsize(backup_path)
                backups.append({
                    'filename': file,
                    'path': backup_path,
                    'created_at': datetime.datetime.fromtimestamp(backup_time),
                    'size': backup_size
                })
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)
    
    def restore_backup(self, backup_path):
        """Restore database from a backup."""
        if not os.path.exists(backup_path):
            return False
            
        self.close_connection()  # Close connection before restore
        shutil.copy2(backup_path, self.db_path)
        return True
    
    # User operations
    def create_user(self, username, password_hash, role, assigned_event_id=None):
        """Create a new user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, assigned_event_id) VALUES (?, ?, ?, ?)",
                (username, password_hash, role, assigned_event_id)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            conn.rollback()
            return None
    
    def get_user(self, username):
        """Get user by username."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cursor.fetchone()
    
    def update_user_last_login(self, user_id):
        """Update user's last login timestamp."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,)
        )
        conn.commit()
    
    def get_all_users(self):
        """Get all users."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, assigned_event_id, created_at, last_login FROM users")
        return cursor.fetchall()
    
    def delete_user(self, user_id):
        """Delete a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    
    # Event operations
    def create_event(self, name, description, date, location, created_by):
        """Create a new event."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO events (name, description, date, location, created_by) VALUES (?, ?, ?, ?, ?)",
            (name, description, date, location, created_by)
        )
        conn.commit()
        return cursor.lastrowid
    
    def get_event(self, event_id):
        """Get event by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        return cursor.fetchone()
    
    def get_all_events(self):
        """Get all events."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events ORDER BY date DESC")
        return cursor.fetchall()
    
    def update_event(self, event_id, name, description, date, location):
        """Update event details."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE events SET name = ?, description = ?, date = ?, location = ? WHERE id = ?",
            (name, description, date, location, event_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    
    def delete_event(self, event_id):
        """Delete an event."""
        conn = self.get_connection()
        cursor = conn.cursor()
        # First delete all participants associated with this event
        cursor.execute("DELETE FROM participants WHERE event_id = ?", (event_id,))
        # Then delete the event
        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
        return cursor.rowcount > 0
    
    # Participant operations
    def add_participant(self, name, email, phone, college, group_name, event_id):
        """Add a new participant."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO participants 
               (name, email, phone, college, group_name, event_id) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, email, phone, college, group_name, event_id)
        )
        conn.commit()
        return cursor.lastrowid
    
    def bulk_add_participants(self, participants_data):
        """Add multiple participants at once."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            for participant in participants_data:
                cursor.execute(
                    """INSERT INTO participants 
                       (name, email, phone, college, group_name, event_id) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        participant.get('name', ''),
                        participant.get('email', ''),
                        participant.get('phone', ''),
                        participant.get('college', ''),
                        participant.get('group_name', ''),
                        participant.get('event_id')
                    )
                )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
    
    def get_participant(self, participant_id):
        """Get participant by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM participants WHERE id = ?", (participant_id,))
        return cursor.fetchone()
    
    def get_participants_by_event(self, event_id):
        """Get all participants for a specific event."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM participants WHERE event_id = ?", (event_id,))
        return cursor.fetchall()
    
    def search_participants(self, search_term, event_id=None):
        """Search participants by name, email, phone, or college."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        
        if event_id:
            cursor.execute(
                """SELECT * FROM participants 
                   WHERE (name LIKE ? OR email LIKE ? OR phone LIKE ? OR college LIKE ? OR group_name LIKE ?) 
                   AND event_id = ?""",
                (search_pattern, search_pattern, search_pattern, search_pattern,search_pattern, event_id)
            )
        else:
            cursor.execute(
                """SELECT * FROM participants 
                   WHERE name LIKE ? OR email LIKE ? OR phone LIKE ? OR college LIKE ? OR group_name LIKE ?""",
                (search_pattern, search_pattern, search_pattern, search_pattern,search_pattern)
            )
        
        return cursor.fetchall()
    
    def update_participant(self, participant_id, name, email, phone, college, group_name, user_id):
        """Update participant details and track changes."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get current data
        cursor.execute("SELECT * FROM participants WHERE id = ?", (participant_id,))
        current_data = cursor.fetchone()
        
        if not current_data:
            return False
        
        # Track changes
        fields_to_update = {
            'name': name,
            'email': email,
            'phone': phone,
            'college': college,
            'group_name': group_name
        }
        
        for field, new_value in fields_to_update.items():
            old_value = current_data[field]
            if old_value != new_value:
                cursor.execute(
                    """INSERT INTO data_history 
                       (participant_id, field_name, old_value, new_value, modified_by) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (participant_id, field, old_value, new_value, user_id)
                )
        
        # Update participant
        cursor.execute(
            """UPDATE participants 
               SET name = ?, email = ?, phone = ?, college = ?, group_name = ? 
               WHERE id = ?""",
            (name, email, phone, college, group_name, participant_id)
        )
        
        conn.commit()
        return True
    
    def check_in_participant(self, participant_id, user_id, id_card_photo=None):
        """Mark a participant as checked in."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get current check-in status
        cursor.execute("SELECT checked_in FROM participants WHERE id = ?", (participant_id,))
        current_status = cursor.fetchone()
        
        if not current_status:
            return False
        
        # Only update if not already checked in
        if not current_status['checked_in']:
            # Prepare query based on whether ID card photo was provided
            if id_card_photo:
                cursor.execute(
                    """UPDATE participants 
                       SET checked_in = 1, check_in_time = CURRENT_TIMESTAMP, id_card_photo = ?
                       WHERE id = ?""",
                    (id_card_photo, participant_id)
                )
            else:
                cursor.execute(
                    """UPDATE participants 
                       SET checked_in = 1, check_in_time = CURRENT_TIMESTAMP 
                       WHERE id = ?""",
                    (participant_id,)
                )
            
            # Track the change
            cursor.execute(
                """INSERT INTO data_history 
                   (participant_id, field_name, old_value, new_value, modified_by) 
                   VALUES (?, ?, ?, ?, ?)""",
                (participant_id, 'checked_in', '0', '1', user_id)
            )
            
            if id_card_photo:
                cursor.execute(
                    """INSERT INTO data_history 
                       (participant_id, field_name, old_value, new_value, modified_by) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (participant_id, 'id_card_photo', None, 'Photo captured', user_id)
                )
            
            conn.commit()
            return True
        
        return False
    
    def undo_check_in(self, participant_id, user_id):
        """Undo a participant check-in."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE participants SET checked_in = 0, check_in_time = NULL, id_card_photo = NULL WHERE id = ?",
            (participant_id,)
        )
        
        # Track the change
        cursor.execute(
            """INSERT INTO data_history 
               (participant_id, field_name, old_value, new_value, modified_by) 
               VALUES (?, ?, ?, ?, ?)""",
            (participant_id, 'checked_in', '1', '0', user_id)
        )
        
        # Track photo removal if applicable
        cursor.execute(
            """INSERT INTO data_history 
               (participant_id, field_name, old_value, new_value, modified_by) 
               VALUES (?, ?, ?, ?, ?)""",
            (participant_id, 'id_card_photo', 'Photo captured', 'Photo removed', user_id)
        )
        
        conn.commit()
        return cursor.rowcount > 0
    
    def delete_participant(self, participant_id):
        """Delete a participant."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Delete history records
        cursor.execute("DELETE FROM data_history WHERE participant_id = ?", (participant_id,))
        
        # Delete participant
        cursor.execute("DELETE FROM participants WHERE id = ?", (participant_id,))
        
        conn.commit()
        return cursor.rowcount > 0
    
    # Dashboard and reporting
    def get_participant_stats(self, event_id=None):
        """Get participant statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if event_id:
            cursor.execute(
                """SELECT COUNT(*) as total, 
                   SUM(checked_in) as checked_in,
                   COUNT(*) - SUM(checked_in) as not_checked_in
                   FROM participants WHERE event_id = ?""",
                (event_id,)
            )
        else:
            cursor.execute(
                """SELECT COUNT(*) as total, 
                   SUM(checked_in) as checked_in,
                   COUNT(*) - SUM(checked_in) as not_checked_in
                   FROM participants"""
            )
        
        return cursor.fetchone()
    
    def get_college_stats(self, event_id=None):
        """Get college-wise statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if event_id:
            cursor.execute(
                """SELECT college, COUNT(*) as total, 
                   SUM(checked_in) as checked_in
                   FROM participants 
                   WHERE event_id = ?
                   GROUP BY college
                   ORDER BY total DESC""",
                (event_id,)
            )
        else:
            cursor.execute(
                """SELECT college, COUNT(*) as total, 
                   SUM(checked_in) as checked_in
                   FROM participants 
                   GROUP BY college
                   ORDER BY total DESC"""
            )
        
        return cursor.fetchall()
    
    def get_event_stats(self):
        """Get event-wise statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT e.id, e.name, 
               COUNT(p.id) as total_participants, 
               SUM(p.checked_in) as checked_in
               FROM events e
               LEFT JOIN participants p ON e.id = p.event_id
               GROUP BY e.id
               ORDER BY total_participants DESC"""
        )
        
        return cursor.fetchall()
    
    def get_check_in_timeline(self, event_id=None, date=None):
        """Get check-in statistics over time."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # If date is not provided, use today
        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        if event_id:
            cursor.execute(
                """SELECT 
                   strftime('%H', check_in_time) as hour,
                   COUNT(*) as count
                   FROM participants
                   WHERE event_id = ? 
                   AND date(check_in_time) = ?
                   AND checked_in = 1
                   GROUP BY hour
                   ORDER BY hour""",
                (event_id, date)
            )
        else:
            cursor.execute(
                """SELECT 
                   strftime('%H', check_in_time) as hour,
                   COUNT(*) as count
                   FROM participants
                   WHERE date(check_in_time) = ?
                   AND checked_in = 1
                   GROUP BY hour
                   ORDER BY hour""",
                (date,)
            )
        
        return cursor.fetchall()
    
    def get_data_modification_history(self, participant_id=None):
        """Get data modification history."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if participant_id:
            cursor.execute(
                """SELECT h.*, p.name as participant_name, u.username as modified_by_username
                   FROM data_history h
                   JOIN participants p ON h.participant_id = p.id
                   JOIN users u ON h.modified_by = u.id
                   WHERE h.participant_id = ?
                   ORDER BY h.modified_at DESC""",
                (participant_id,)
            )
        else:
            cursor.execute(
                """SELECT h.*, p.name as participant_name, u.username as modified_by_username
                   FROM data_history h
                   JOIN participants p ON h.participant_id = p.id
                   JOIN users u ON h.modified_by = u.id
                   ORDER BY h.modified_at DESC
                   LIMIT 100"""
            )
        
        return cursor.fetchall()
    
    def get_id_card_photo(self, participant_id):
        """Get ID card photo for a participant."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id_card_photo FROM participants WHERE id = ?", (participant_id,))
        result = cursor.fetchone()
        
        if result and result['id_card_photo']:
            return result['id_card_photo']
        
        return None
    
    def export_participants_data(self, event_id=None):
        """Export participants data as a pandas DataFrame."""
        conn = self.get_connection()
        
        if event_id:
            query = f"""
                SELECT p.*, e.name as event_name
                FROM participants p
                JOIN events e ON p.event_id = e.id
                WHERE p.event_id = {event_id}
            """
        else:
            query = """
                SELECT p.*, e.name as event_name
                FROM participants p
                JOIN events e ON p.event_id = e.id
            """
        
        return pd.read_sql_query(query, conn)
    def get_all_participants(self, event_id=None):
        """Get all participants, optionally filtered by event."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if event_id:
            cursor.execute(
                """SELECT p.*, e.name as event_name 
                FROM participants p
                JOIN events e ON p.event_id = e.id
                WHERE p.event_id = ?
                ORDER BY p.name""", 
                (event_id,)
            )
        else:
            cursor.execute(
                """SELECT p.*, e.name as event_name 
                FROM participants p
                JOIN events e ON p.event_id = e.id
                ORDER BY p.name"""
            )
        
        return cursor.fetchall()
    def update_participant_full(self, participant_id, name, email, phone, college, group_name, 
                           event_id, checked_in, user_id):
        """Update all participant details and track changes."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get current data
        cursor.execute("SELECT * FROM participants WHERE id = ?", (participant_id,))
        current_data = cursor.fetchone()
        
        if not current_data:
            return False
        
        # Track changes
        fields_to_update = {
            'name': name,
            'email': email,
            'phone': phone,
            'college': college,
            'group_name': group_name,
            'event_id': event_id,
            'checked_in': checked_in
        }
        
        for field, new_value in fields_to_update.items():
            old_value = current_data[field]
            if str(old_value) != str(new_value):  # Convert to string for comparison
                cursor.execute(
                    """INSERT INTO data_history 
                    (participant_id, field_name, old_value, new_value, modified_by) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (participant_id, field, str(old_value), str(new_value), user_id)
                )
        
        # Update check_in_time if checked_in status changed
        check_in_time_clause = ""
        params = [name, email, phone, college, group_name, event_id, checked_in]
        
        # If changing from not checked in to checked in, update the timestamp
        if not current_data['checked_in'] and checked_in:
            check_in_time_clause = ", check_in_time = CURRENT_TIMESTAMP"
        # If changing from checked in to not checked in, clear the timestamp
        elif current_data['checked_in'] and not checked_in:
            check_in_time_clause = ", check_in_time = NULL"
        
        # Update participant
        cursor.execute(
            f"""UPDATE participants 
            SET name = ?, email = ?, phone = ?, college = ?, group_name = ?, 
                event_id = ?, checked_in = ? {check_in_time_clause}
            WHERE id = ?""",
            params + [participant_id]
        )
        
        conn.commit()
        return True