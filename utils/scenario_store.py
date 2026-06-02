import sqlite3
import json
import datetime
import hashlib
from pathlib import Path


DB_PATH = Path("data/vidyut_vahanastra_scenarios.db")


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def create_scenario_hash(scenario_data):
    """
    Creates deterministic SHA-256 hash for scenario JSON.
    sort_keys=True ensures same content gives same hash even if key order changes.
    """
    canonical_json = json.dumps(
        scenario_data,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def init_scenario_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_name TEXT NOT NULL,
            vehicle_segment TEXT,
            chemistry TEXT,
            pack_voltage REAL,
            pack_energy REAL,
            estimated_range REAL,
            charging_time REAL,
            wh_per_km REAL,
            scenario_data TEXT NOT NULL,
            scenario_hash TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()

    # Migration for older databases that do not have scenario_hash column.
    cursor.execute("PRAGMA table_info(scenarios)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    if "scenario_hash" not in existing_columns:
        cursor.execute("ALTER TABLE scenarios ADD COLUMN scenario_hash TEXT")
        conn.commit()

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_scenario_hash
        ON scenarios (scenario_hash)
        """
    )

    conn.commit()
    conn.close()


def scenario_hash_exists(scenario_hash):
    init_scenario_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, scenario_name, created_at
        FROM scenarios
        WHERE scenario_hash = ?
        LIMIT 1
        """,
        (scenario_hash,)
    )

    row = cursor.fetchone()
    conn.close()

    return row


def save_scenario(
    scenario_name,
    vehicle_segment,
    chemistry,
    pack_voltage,
    pack_energy,
    estimated_range,
    charging_time,
    wh_per_km,
    scenario_data,
    skip_duplicates=False
):
    init_scenario_db()

    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scenario_json = json.dumps(scenario_data, indent=4)
    scenario_hash = create_scenario_hash(scenario_data)

    existing = scenario_hash_exists(scenario_hash)

    if skip_duplicates and existing is not None:
        return {
            "saved": False,
            "duplicate": True,
            "existing_id": existing[0],
            "existing_name": existing[1],
            "existing_created_at": existing[2],
            "scenario_hash": scenario_hash
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO scenarios (
            scenario_name,
            vehicle_segment,
            chemistry,
            pack_voltage,
            pack_energy,
            estimated_range,
            charging_time,
            wh_per_km,
            scenario_data,
            scenario_hash,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scenario_name,
            vehicle_segment,
            chemistry,
            pack_voltage,
            pack_energy,
            estimated_range,
            charging_time,
            wh_per_km,
            scenario_json,
            scenario_hash,
            created_at
        )
    )

    inserted_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "saved": True,
        "duplicate": False,
        "inserted_id": inserted_id,
        "scenario_hash": scenario_hash
    }


def list_scenarios():
    init_scenario_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            id,
            scenario_name,
            vehicle_segment,
            chemistry,
            pack_voltage,
            pack_energy,
            estimated_range,
            charging_time,
            wh_per_km,
            created_at
        FROM scenarios
        ORDER BY id DESC
        """
    )

    rows = cursor.fetchall()
    conn.close()

    columns = [
        "ID",
        "Scenario Name",
        "Vehicle Segment",
        "Chemistry",
        "Pack Voltage (V)",
        "Pack Energy (kWh)",
        "Estimated Range (km)",
        "Charging Time (min)",
        "Wh/km",
        "Created At"
    ]

    return rows, columns


def list_scenarios_with_hash():
    init_scenario_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            id,
            scenario_name,
            vehicle_segment,
            chemistry,
            pack_voltage,
            pack_energy,
            estimated_range,
            charging_time,
            wh_per_km,
            scenario_hash,
            created_at
        FROM scenarios
        ORDER BY id DESC
        """
    )

    rows = cursor.fetchall()
    conn.close()

    columns = [
        "ID",
        "Scenario Name",
        "Vehicle Segment",
        "Chemistry",
        "Pack Voltage (V)",
        "Pack Energy (kWh)",
        "Estimated Range (km)",
        "Charging Time (min)",
        "Wh/km",
        "Scenario Hash",
        "Created At"
    ]

    return rows, columns


def get_scenario_by_id(scenario_id):
    init_scenario_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT scenario_data 
        FROM scenarios 
        WHERE id = ?
        """,
        (scenario_id,)
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return json.loads(row[0])


def delete_scenario(scenario_id):
    init_scenario_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM scenarios 
        WHERE id = ?
        """,
        (scenario_id,)
    )

    conn.commit()
    conn.close()