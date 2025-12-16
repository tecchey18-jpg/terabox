"""
Database for storing user data and analytics
"""

import aiosqlite
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

from config import config

logger = logging.getLogger(__name__)


@dataclass
class User:
    user_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    joined_at: datetime
    total_requests: int = 0
    last_request: Optional[datetime] = None


@dataclass
class RequestLog:
    id: int
    user_id: int
    url: str
    success: bool
    error_message: Optional[str]
    created_at: datetime


class Database:
    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path
        self._lock = asyncio.Lock()
    
    async def init(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_requests INTEGER DEFAULT 0,
                    last_request TIMESTAMP
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS request_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    url TEXT,
                    success BOOLEAN,
                    error_message TEXT,
                    video_title TEXT,
                    video_size INTEGER,
                    extraction_method TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    share_id TEXT PRIMARY KEY,
                    video_info TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            ''')
            
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_request_logs_user_id 
                ON request_logs (user_id)
            ''')
            
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_request_logs_created_at 
                ON request_logs (created_at)
            ''')
            
            await db.commit()
    
    async def add_user(self, user_id: int, username: str, first_name: str, last_name: str = None):
        """Add or update user"""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = excluded.username,
                        first_name = excluded.first_name,
                        last_name = excluded.last_name
                ''', (user_id, username, first_name, last_name))
                await db.commit()
    
    async def log_request(
        self,
        user_id: int,
        url: str,
        success: bool,
        error_message: str = None,
        video_title: str = None,
        video_size: int = None,
        extraction_method: str = None
    ):
        """Log a request"""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO request_logs 
                    (user_id, url, success, error_message, video_title, video_size, extraction_method)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, url, success, error_message, video_title, video_size, extraction_method))
                
                await db.execute('''
                    UPDATE users 
                    SET total_requests = total_requests + 1,
                        last_request = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
                
                await db.commit()
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            async with db.execute(
                'SELECT * FROM users WHERE user_id = ?', (user_id,)
            ) as cursor:
                user_row = await cursor.fetchone()
            
            if not user_row:
                return {}
            
            async with db.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed
                FROM request_logs WHERE user_id = ?
            ''', (user_id,)) as cursor:
                stats_row = await cursor.fetchone()
            
            return {
                "user": dict(user_row),
                "total_requests": stats_row["total"] or 0,
                "successful": stats_row["successful"] or 0,
                "failed": stats_row["failed"] or 0,
            }
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT COUNT(*) FROM users') as cursor:
                total_users = (await cursor.fetchone())[0]
            
            async with db.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
                FROM request_logs
            ''') as cursor:
                row = await cursor.fetchone()
                total_requests = row[0] or 0
                successful_requests = row[1] or 0
            
            async with db.execute('''
                SELECT COUNT(*) FROM request_logs 
                WHERE created_at > datetime('now', '-24 hours')
            ''') as cursor:
                requests_24h = (await cursor.fetchone())[0]
            
            return {
                "total_users": total_users,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
                "requests_24h": requests_24h,
            }


# Singleton
db = Database()
