"""
G-code Program Storage Module

SQLite-based storage for generated G-code programs.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
import json
import logging

logger = logging.getLogger(__name__)


class GCodeDatabase:
    """SQLite database for storing and retrieving G-code programs."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database.
        
        Args:
            db_path: Path to the SQLite database file. 
                     If None, uses output/programs.db
        """
        if db_path is None:
            # Use project's output directory
            base_dir = Path(__file__).parent.parent.parent
            db_path = base_dir / "output" / "programs.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        logger.info(f"GCodeDatabase initialized at: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialize database schema."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Create programs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS programs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    content TEXT NOT NULL,
                    material TEXT,
                    operations TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Create index on created_at for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_programs_created_at 
                ON programs(created_at DESC)
            """)
            
            # Create index on material for filtering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_programs_material 
                ON programs(material)
            """)
            
            conn.commit()
            logger.info("Database schema initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
        finally:
            conn.close()
    
    def save_program(
        self,
        filename: str,
        content: str,
        material: str = "45#钢",
        operations: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Save a generated G-code program to the database.
        
        Args:
            filename: Program filename (e.g., O0001.nc)
            content: The actual G-code content
            material: Material type used
            operations: List of machining operations
            metadata: Additional metadata as dictionary
            
        Returns:
            The ID of the newly inserted program, or raises exception on error
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            created_at = datetime.now().isoformat()
            operations_json = json.dumps(operations) if operations else None
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute("""
                INSERT INTO programs (
                    filename, content, material, operations, created_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                filename,
                content,
                material,
                operations_json,
                created_at,
                metadata_json
            ))
            
            conn.commit()
            program_id = cursor.lastrowid
            logger.info(f"Program saved: ID={program_id}, filename={filename}")
            return program_id
            
        except Exception as e:
            logger.error(f"Failed to save program: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_program(self, program_id: int) -> Optional[Dict]:
        """
        Retrieve a program by ID.
        
        Args:
            program_id: Program database ID
            
        Returns:
            Program data as dictionary, or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM programs WHERE id = ?
            """, (program_id,))
            
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            # Convert to dictionary
            program = dict(row)
            
            # Parse JSON fields
            if program.get('operations'):
                program['operations'] = json.loads(program['operations'])
            if program.get('metadata'):
                program['metadata'] = json.loads(program['metadata'])
            
            return program
            
        except Exception as e:
            logger.error(f"Failed to retrieve program: {e}")
            return None
        finally:
            conn.close()
    
    def list_programs(
        self,
        limit: int = 50,
        offset: int = 0,
        material: Optional[str] = None
    ) -> List[Dict]:
        """
        List programs with optional filtering.
        
        Args:
            limit: Maximum number of programs to return
            offset: Number of programs to skip
            material: Filter by material type
            
        Returns:
            List of program summaries (without full content)
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            if material:
                cursor.execute("""
                    SELECT id, filename, material, created_at
                    FROM programs
                    WHERE material = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (material, limit, offset))
            else:
                cursor.execute("""
                    SELECT id, filename, material, created_at
                    FROM programs
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            rows = cursor.fetchall()
            
            programs = []
            for row in rows:
                program = dict(row)
                programs.append(program)
            
            return programs
            
        except Exception as e:
            logger.error(f"Failed to list programs: {e}")
            return []
        finally:
            conn.close()
    
    def delete_program(self, program_id: int) -> bool:
        """
        Delete a program by ID.
        
        Args:
            program_id: Program database ID
            
        Returns:
            True if deleted, False if not found or error
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM programs WHERE id = ?
            """, (program_id,))
            
            deleted = cursor.rowcount > 0
            conn.commit()
            
            if deleted:
                logger.info(f"Program deleted: {program_id}")
            else:
                logger.warning(f"Program not found: {program_id}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete program: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_program_count(self) -> int:
        """Get total number of programs in database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM programs")
            row = cursor.fetchone()
            
            return row['count'] if row else 0
            
        except Exception as e:
            logger.error(f"Failed to get program count: {e}")
            return 0
        finally:
            conn.close()
    
    def search_programs(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search programs by program name or material.
        
        Args:
            query: Search query string
            limit: Maximum results to return
            
        Returns:
            List of matching program summaries
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            search_pattern = f"%{query}%"
            
            cursor.execute("""
                SELECT id, program_name, material, machine_system,
                       start_diameter, end_diameter, length, 
                       lines, created_at
                FROM programs
                WHERE program_name LIKE ? OR material LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (search_pattern, search_pattern, limit))
            
            rows = cursor.fetchall()
            
            programs = [dict(row) for row in rows]
            return programs
            
        except Exception as e:
            logger.error(f"Failed to search programs: {e}")
            return []
        finally:
            conn.close()
