"""Database connection and management."""

import asyncio
import logging
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

# Database singleton
_database: "Database | None" = None


class Database:
    """
    Async SQLite database manager.

    Handles connection pooling and provides async context management.
    """

    def __init__(self, db_path: str = "health_monitor.db"):
        self.db_path = db_path
        self._connection: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Establish database connection."""
        async with self._lock:
            if self._connection is None:
                self._connection = await aiosqlite.connect(self.db_path)
                self._connection.row_factory = aiosqlite.Row
                await self._connection.execute("PRAGMA foreign_keys = ON")
                logger.info(f"Connected to database: {self.db_path}")

    async def disconnect(self) -> None:
        """Close database connection."""
        async with self._lock:
            if self._connection:
                await self._connection.close()
                self._connection = None
                logger.info("Database connection closed")

    async def execute(
        self,
        query: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> aiosqlite.Cursor:
        """Execute a query."""
        if not self._connection:
            await self.connect()
        return await self._connection.execute(query, params or ())

    async def executemany(
        self,
        query: str,
        params_list: list[tuple[Any, ...]]
    ) -> aiosqlite.Cursor:
        """Execute a query with multiple parameter sets."""
        if not self._connection:
            await self.connect()
        return await self._connection.executemany(query, params_list)

    async def fetchone(
        self,
        query: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> aiosqlite.Row | None:
        """Fetch a single row."""
        cursor = await self.execute(query, params)
        return await cursor.fetchone()

    async def fetchall(
        self,
        query: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> list[aiosqlite.Row]:
        """Fetch all rows."""
        cursor = await self.execute(query, params)
        return await cursor.fetchall()

    async def commit(self) -> None:
        """Commit the current transaction."""
        if self._connection:
            await self._connection.commit()

    async def init_schema(self) -> None:
        """Initialize database schema."""
        await self.connect()

        # Patients table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                date_of_birth DATE NOT NULL,
                gender TEXT,
                height_cm REAL,
                weight_kg REAL,
                blood_type TEXT,
                emergency_contact_name TEXT,
                emergency_contact_phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Medical conditions table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS medical_conditions (
                condition_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                name TEXT NOT NULL,
                diagnosed_date DATE,
                status TEXT DEFAULT 'active',
                severity TEXT DEFAULT 'moderate',
                notes TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
        """)

        # Allergies table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS allergies (
                allergy_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                allergen TEXT NOT NULL,
                reaction_type TEXT,
                severity TEXT,
                notes TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
        """)

        # Vital readings table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS vital_readings (
                reading_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                vital_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                device_id TEXT,
                notes TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
        """)

        # Create index for faster vital queries
        await self.execute("""
            CREATE INDEX IF NOT EXISTS idx_vital_readings_patient_type
            ON vital_readings(patient_id, vital_type, recorded_at)
        """)

        # Medications table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS medications (
                medication_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                name TEXT NOT NULL,
                dosage TEXT NOT NULL,
                frequency TEXT NOT NULL,
                scheduled_times TEXT,
                start_date DATE NOT NULL,
                end_date DATE,
                instructions TEXT,
                prescriber TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
        """)

        # Dose records table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS dose_records (
                record_id TEXT PRIMARY KEY,
                medication_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                scheduled_time TIMESTAMP NOT NULL,
                status TEXT NOT NULL,
                actual_time TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (medication_id) REFERENCES medications(medication_id) ON DELETE CASCADE,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
        """)

        # Symptoms table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS symptoms (
                symptom_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                severity INTEGER NOT NULL,
                description TEXT,
                location TEXT,
                onset_time TIMESTAMP,
                duration_hours REAL,
                triggers TEXT,
                reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
        """)

        # Alerts table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                category TEXT NOT NULL,
                severity INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                source_agent TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged_at TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
        """)

        # Activities table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                activity_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                calories_burned INTEGER,
                distance_km REAL,
                intensity TEXT,
                notes TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
        """)

        # Sleep records table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS sleep_records (
                sleep_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                sleep_start TIMESTAMP NOT NULL,
                sleep_end TIMESTAMP NOT NULL,
                total_hours REAL NOT NULL,
                quality INTEGER NOT NULL,
                awakenings INTEGER DEFAULT 0,
                notes TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
        """)

        # Daily steps table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS daily_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                date DATE NOT NULL,
                steps INTEGER NOT NULL,
                UNIQUE(patient_id, date),
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
        """)

        await self.commit()
        logger.info("Database schema initialized")


async def get_database() -> Database:
    """Get or create database singleton."""
    global _database
    if _database is None:
        _database = Database()
        await _database.init_schema()
    return _database
