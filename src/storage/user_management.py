"""
User Management System for CAD to G-code Platform

Implements user authentication, session management, and multi-user isolation.
Features:
- User registration and login
- Password hashing with bcrypt
- JWT token-based authentication
- User-specific program isolation
- Role-based access control (admin/user)
"""

import sqlite3
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging
from dataclasses import dataclass

try:
    import bcrypt
except ImportError:
    raise ImportError("bcrypt is required. Install with: pip install bcrypt")

logger = logging.getLogger(__name__)


@dataclass
class User:
    """User data structure."""
    id: int
    username: str
    email: str
    role: str  # 'admin' or 'user'
    created_at: str
    last_login: Optional[str] = None


class UserDatabase:
    """User database manager with authentication support."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.jwt_secret = secrets.token_hex(32)  # In production, load from env
        self._initialize_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _initialize_schema(self):
        """Initialize database schema for users and sessions."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Sessions table (for token management)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_valid BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    default_material TEXT DEFAULT '45#钢',
                    default_machine_system TEXT DEFAULT 'FANUC',
                    theme TEXT DEFAULT 'light',
                    language TEXT DEFAULT 'zh-CN',
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Add user_id to programs table if not exists
            try:
                cursor.execute("""
                    PRAGMA table_info(programs)
                """)
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'user_id' not in columns:
                    logger.info("Adding user_id column to programs table")
                    cursor.execute("""
                        ALTER TABLE programs ADD COLUMN user_id INTEGER
                    """)
                    cursor.execute("""
                        UPDATE programs SET user_id = 0 WHERE user_id IS NULL
                    """)
            except Exception as e:
                logger.info(f"Skipping user_id column addition: {e}")
            
            # Create indexes for performance
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_programs_user_id ON programs(user_id)
                """)
            except Exception as e:
                logger.info(f"Skipping programs index creation: {e}")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)
            """)
            
            # Create default admin user if no users exist
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                logger.info("Creating default admin user")
                admin_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (?, ?, ?, ?)
                """, ("admin", "admin@example.com", admin_hash, "admin"))
                
                # Create default preferences for admin
                cursor.execute("""
                    INSERT INTO user_preferences (user_id, default_material, default_machine_system)
                    VALUES (1, '45#钢', 'FANUC')
                """)
            
            conn.commit()
            logger.info("User database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing user database: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def create_user(self, username: str, email: str, password: str, role: str = 'user') -> Optional[int]:
        """Create a new user."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                logger.warning(f"User {username} or email {email} already exists")
                return None
            
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Insert user
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (?, ?, ?, ?)
            """, (username, email, password_hash, role))
            
            user_id = cursor.lastrowid
            
            # Create default preferences
            cursor.execute("""
                INSERT INTO user_preferences (user_id)
                VALUES (?)
            """, (user_id,))
            
            conn.commit()
            logger.info(f"User {username} created successfully with ID {user_id}")
            return user_id
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return JWT token."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Get user
            cursor.execute("""
                SELECT id, username, email, role, password_hash, is_active
                FROM users
                WHERE username = ?
            """, (username,))
            
            user_row = cursor.fetchone()
            if not user_row:
                logger.warning(f"User {username} not found")
                return None
            
            user_dict = dict(user_row)
            
            if not user_dict['is_active']:
                logger.warning(f"User {username} is inactive")
                return None
            
            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), user_dict['password_hash'].encode('utf-8')):
                logger.warning(f"Invalid password for user {username}")
                return None
            
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_dict['id'],))
            
            conn.commit()
            
            # Generate JWT token
            token_data = {
                'user_id': user_dict['id'],
                'username': user_dict['username'],
                'role': user_dict['role'],
                'exp': datetime.utcnow() + timedelta(hours=24)
            }
            
            token = jwt.encode(token_data, self.jwt_secret, algorithm='HS256')
            
            # Store session
            cursor.execute("""
                INSERT INTO sessions (user_id, token, expires_at)
                VALUES (?, ?, ?)
            """, (user_dict['id'], token, token_data['exp']))
            
            conn.commit()
            
            logger.info(f"User {username} authenticated successfully")
            
            return {
                'token': token,
                'user': {
                    'id': user_dict['id'],
                    'username': user_dict['username'],
                    'email': user_dict['email'],
                    'role': user_dict['role']
                }
            }
            
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return user info."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Check if session is valid
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.is_valid, u.is_active
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = ?
            """, (token,))
            
            session = cursor.fetchone()
            conn.close()
            
            if not session or not session[0] or not session[1]:
                return None
            
            return {
                'user_id': payload['user_id'],
                'username': payload['username'],
                'role': payload['role']
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def logout(self, token: str) -> bool:
        """Invalidate session token."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions SET is_valid = 0 WHERE token = ?
            """, (token,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error logging out: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, role, created_at, last_login
                FROM users
                WHERE id = ? AND is_active = 1
            """, (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return User(**dict(row))
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
        finally:
            conn.close()
    
    def get_user_preferences(self, user_id: int) -> Dict[str, str]:
        """Get user preferences."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT default_material, default_machine_system, theme, language
                FROM user_preferences
                WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return {}
            
            return {
                'default_material': row[0],
                'default_machine_system': row[1],
                'theme': row[2],
                'language': row[3]
            }
        except Exception as e:
            logger.error(f"Error getting preferences: {e}")
            return {}
        finally:
            conn.close()
    
    def update_user_preferences(self, user_id: int, preferences: Dict[str, str]) -> bool:
        """Update user preferences."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_preferences
                SET default_material = COALESCE(?, default_material),
                    default_machine_system = COALESCE(?, default_machine_system),
                    theme = COALESCE(?, theme),
                    language = COALESCE(?, language)
                WHERE user_id = ?
            """, (
                preferences.get('default_material'),
                preferences.get('default_machine_system'),
                preferences.get('theme'),
                preferences.get('language'),
                user_id
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def list_users(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List all users (admin only)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, role, created_at, last_login, is_active
                FROM users
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
        finally:
            conn.close()
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user (admin only)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET is_active = 0 WHERE id = ?
            """, (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()


# Singleton instance
_user_db: Optional[UserDatabase] = None


def get_user_database(db_path: str = None) -> UserDatabase:
    """Get or create user database singleton."""
    global _user_db
    
    if _user_db is None:
        if db_path is None:
            db_path = Path(__file__).parent.parent / 'data' / 'users.db'
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        _user_db = UserDatabase(str(db_path))
    
    return _user_db
