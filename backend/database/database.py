import os
import time
import sqlite3
from pathlib import Path

from backend.config import BASE_DIR


# ============================================================
# DATABASE PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATABASE_PATH = Path(os.getenv("CLIPFINDER_DB_PATH", str(BASE_DIR / "clipfinder.db"))).resolve()


# ============================================================
# CONNECTION
# ============================================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    return connection



# ============================================================
# INIT DATABASE
# ============================================================

def init_database():

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS videos (

            id TEXT PRIMARY KEY,

            title TEXT NOT NULL DEFAULT '',

            channel TEXT NOT NULL DEFAULT '',

            thumbnail TEXT NOT NULL DEFAULT '',

            url TEXT NOT NULL DEFAULT '',

            views INTEGER NOT NULL DEFAULT 0,

            published_at TEXT NOT NULL DEFAULT '',

            duration TEXT NOT NULL DEFAULT '',


            is_short INTEGER NOT NULL DEFAULT 0,

            is_4k INTEGER NOT NULL DEFAULT 0,

            is_hd INTEGER NOT NULL DEFAULT 0,

            is_clean INTEGER NOT NULL DEFAULT 0,

            is_action INTEGER NOT NULL DEFAULT 0,


            is_clip INTEGER NOT NULL DEFAULT 0,

            is_cinematic INTEGER NOT NULL DEFAULT 0,

            is_gameplay INTEGER NOT NULL DEFAULT 0,

            is_dynamic INTEGER NOT NULL DEFAULT 0,


            has_music INTEGER NOT NULL DEFAULT 0,

            has_voice INTEGER NOT NULL DEFAULT 0,

            has_dialogue INTEGER NOT NULL DEFAULT 0,


            is_raw_footage INTEGER NOT NULL DEFAULT 0,

            is_no_music INTEGER NOT NULL DEFAULT 0,


            score REAL NOT NULL DEFAULT 0,

            edit_score REAL NOT NULL DEFAULT 0,


            query TEXT NOT NULL DEFAULT '',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP

        )
        """
    )


    cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_query ON videos(query)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            csrf_token TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires ON auth_sessions(expires_at)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            ip_address TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'new',
            delivery TEXT NOT NULL DEFAULT 'saved',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contact_messages_created ON contact_messages(created_at)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rate_limits (
            rate_key TEXT PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0,
            window_started_at REAL NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS search_state (
            query_key TEXT PRIMARY KEY,
            next_page_token TEXT DEFAULT '',
            youtube_total INTEGER DEFAULT 0,
            pages_loaded INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_favorites (
            user_id INTEGER NOT NULL,
            video_id TEXT NOT NULL,
            video_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, video_id)
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_favorites_user ON user_favorites(user_id)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_collections_user ON collections(user_id)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS collection_items (
            collection_id INTEGER NOT NULL,
            video_id TEXT NOT NULL,
            video_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (collection_id, video_id)
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_collection_items_collection ON collection_items(collection_id)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            query TEXT NOT NULL,
            params_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_user_created ON search_history(user_id, created_at)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS saved_filters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            query TEXT NOT NULL DEFAULT '',
            filters_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_saved_filters_user ON saved_filters(user_id)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            video_id TEXT NOT NULL,
            video_json TEXT NOT NULL,
            start_seconds REAL NOT NULL DEFAULT 0,
            end_seconds REAL NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_user_video ON bookmarks(user_id, video_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_user_created ON bookmarks(user_id, created_at)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS character_catalog (
            slug TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            short_name TEXT NOT NULL DEFAULT '',
            house TEXT NOT NULL DEFAULT '',
            query TEXT NOT NULL DEFAULT '',
            image TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            lore_json TEXT NOT NULL DEFAULT '[]',
            edit_profile_json TEXT NOT NULL DEFAULT '["drama"]',
            status TEXT NOT NULL DEFAULT 'ready',
            portrait_source_type TEXT NOT NULL DEFAULT 'unknown',
            portrait_source_url TEXT NOT NULL DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_character_catalog_status ON character_catalog(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_character_catalog_name ON character_catalog(name COLLATE NOCASE)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS character_generation_guard (
            bucket_date TEXT PRIMARY KEY,
            generated_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS video_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            video_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            resolved_at TEXT,
            resolved_by INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(resolved_by) REFERENCES users(id) ON DELETE SET NULL
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_reports_status_created ON video_reports(status, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_reports_video ON video_reports(video_id, created_at)")

    connection.commit()

    connection.close()




# ============================================================
# SEARCH STATE
# ============================================================

def get_search_state(query_key):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT * FROM search_state WHERE query_key = ?",
        (query_key,),
    )
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None


def save_search_state(query_key, next_page_token, youtube_total, pages_loaded):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO search_state (query_key, next_page_token, youtube_total, pages_loaded, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(query_key) DO UPDATE SET
            next_page_token=excluded.next_page_token,
            youtube_total=excluded.youtube_total,
            pages_loaded=excluded.pages_loaded,
            updated_at=CURRENT_TIMESTAMP
        """ ,
        (query_key, str(next_page_token or ""), int(youtube_total or 0), int(pages_loaded or 0)),
    )
    connection.commit()
    connection.close()


# ============================================================
# ENSURE COLUMN
# ============================================================

def ensure_column(
    cursor,
    table,
    column,
    definition,
):

    cursor.execute(
        f"PRAGMA table_info({table})"
    )


    columns = [

        row["name"]

        for row in cursor.fetchall()

    ]


    if column not in columns:

        cursor.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN {column}
            {definition}
            """
        )




# ============================================================
# MIGRATION
# ============================================================

def migrate_database():

    connection = get_connection()

    cursor = connection.cursor()


    fields = {


        "is_short":
            "INTEGER DEFAULT 0",


        "is_4k":
            "INTEGER DEFAULT 0",


        "is_hd":
            "INTEGER DEFAULT 0",


        "is_clean":
            "INTEGER DEFAULT 0",


        "is_action":
            "INTEGER DEFAULT 0",



        "is_clip":
            "INTEGER DEFAULT 0",


        "is_cinematic":
            "INTEGER DEFAULT 0",


        "is_gameplay":
            "INTEGER DEFAULT 0",


        "is_dynamic":
            "INTEGER DEFAULT 0",



        "has_music":
            "INTEGER DEFAULT 0",


        "has_voice":
            "INTEGER DEFAULT 0",


        "has_dialogue":
            "INTEGER DEFAULT 0",



        "is_raw_footage":
            "INTEGER DEFAULT 0",


        "is_no_music":
            "INTEGER DEFAULT 0",

        "music_confidence":
            "TEXT DEFAULT 'unknown'",

        "voice_confidence":
            "TEXT DEFAULT 'unknown'",

        "dialogue_confidence":
            "TEXT DEFAULT 'unknown'",

        "music_source":
            "TEXT DEFAULT 'metadata'",

        "voice_source":
            "TEXT DEFAULT 'metadata'",

        "dialogue_source":
            "TEXT DEFAULT 'metadata'",

        "description":
            "TEXT DEFAULT ''",

        "score":
            "REAL DEFAULT 0",


        "edit_score":
            "REAL DEFAULT 0",


        "query":
            "TEXT DEFAULT ''",


        "created_at":
            "TEXT DEFAULT CURRENT_TIMESTAMP",

    }



    for name, definition in fields.items():

        ensure_column(
            cursor,
            "videos",
            name,
            definition,
        )



    connection.commit()

    connection.close()





# ============================================================
# START DATABASE
# ============================================================

init_database()

migrate_database()
# ============================================================
# SAVE VIDEOS
# ============================================================

def save_videos(
    videos,
    query,
):
    """Save a complete normalized candidate pool without deleting existing columns."""
    if not videos:
        return

    connection = get_connection()
    cursor = connection.cursor()

    sql = """
        INSERT INTO videos (
            id, title, channel, thumbnail, url, views, published_at, duration,
            description,
            is_short, is_4k, is_hd, is_clean, is_action,
            is_clip, is_cinematic, is_gameplay, is_dynamic,
            has_music, has_voice, has_dialogue,
            is_raw_footage, is_no_music,
            music_confidence, voice_confidence, dialogue_confidence,
            music_source, voice_source, dialogue_source,
            score, edit_score, query
        )
        VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            channel=excluded.channel,
            thumbnail=excluded.thumbnail,
            url=excluded.url,
            views=excluded.views,
            published_at=excluded.published_at,
            duration=excluded.duration,
            description=excluded.description,
            is_short=excluded.is_short,
            is_4k=excluded.is_4k,
            is_hd=excluded.is_hd,
            is_clean=excluded.is_clean,
            is_action=excluded.is_action,
            is_clip=excluded.is_clip,
            is_cinematic=excluded.is_cinematic,
            is_gameplay=excluded.is_gameplay,
            is_dynamic=excluded.is_dynamic,
            has_music=excluded.has_music,
            has_voice=excluded.has_voice,
            has_dialogue=excluded.has_dialogue,
            is_raw_footage=excluded.is_raw_footage,
            is_no_music=excluded.is_no_music,
            music_confidence=excluded.music_confidence,
            voice_confidence=excluded.voice_confidence,
            dialogue_confidence=excluded.dialogue_confidence,
            music_source=excluded.music_source,
            voice_source=excluded.voice_source,
            dialogue_source=excluded.dialogue_source,
            score=excluded.score,
            edit_score=excluded.edit_score,
            query=excluded.query,
            created_at=CURRENT_TIMESTAMP
    """

    for video in videos:
        video_id = str(video.get("id", "") or "").strip()
        if not video_id:
            continue

        def as_int(value):
            try:
                return int(value or 0)
            except (TypeError, ValueError):
                return 0

        def as_float(value):
            try:
                return float(value or 0)
            except (TypeError, ValueError):
                return 0.0

        flags = [
            "is_short", "is_4k", "is_hd", "is_clean", "is_action",
            "is_clip", "is_cinematic", "is_gameplay", "is_dynamic",
            "has_music", "has_voice", "has_dialogue",
            "is_raw_footage", "is_no_music",
        ]

        values = (
            video_id,
            str(video.get("title", "") or ""),
            str(video.get("channel", "") or ""),
            str(video.get("thumbnail", "") or ""),
            str(video.get("url", "") or ""),
            as_int(video.get("views", 0)),
            str(video.get("published_at", "") or ""),
            str(video.get("duration", "") or ""),
            str(video.get("description", "") or ""),
            *[int(bool(video.get(flag, False))) for flag in flags],
            str(video.get("music_confidence", "unknown") or "unknown"),
            str(video.get("voice_confidence", "unknown") or "unknown"),
            str(video.get("dialogue_confidence", "unknown") or "unknown"),
            str(video.get("music_source", "metadata") or "metadata"),
            str(video.get("voice_source", "metadata") or "metadata"),
            str(video.get("dialogue_source", "metadata") or "metadata"),
            as_float(video.get("score", 0)),
            as_float(video.get("edit_score", 0)),
            str(query or ""),
        )
        cursor.execute(sql, values)

    connection.commit()
    connection.close()

# ============================================================
# CACHE CLEANUP
# ============================================================

def cleanup_cache(max_hours=24):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM videos WHERE datetime(created_at) < datetime('now', ?)",
        (f"-{int(max_hours)} hours",),
    )
    cursor.execute(
        "DELETE FROM search_state WHERE datetime(updated_at) < datetime('now', ?)",
        (f"-{max(int(max_hours), 24)} hours",),
    )
    cursor.execute("DELETE FROM auth_sessions WHERE datetime(expires_at) <= datetime('now')")
    cursor.execute(
        "DELETE FROM rate_limits WHERE window_started_at < ?",
        (time.time() - 24 * 60 * 60,),
    )
    connection.commit()
    connection.close()


# ============================================================
# GET CACHED VIDEOS
# ============================================================

def get_cached_videos(
    query,
):


    connection = get_connection()

    cursor = connection.cursor()



    cursor.execute(
        """

        SELECT *

        FROM videos

        WHERE query = ?
        AND datetime(created_at) >= datetime('now', '-24 hours')

        ORDER BY

            edit_score DESC,

            score DESC

        """,

        (

            query,

        )

    )



    rows = cursor.fetchall()


    connection.close()



    results = []



    for row in rows:


        video = dict(row)



        bool_fields = [

            "is_short",

            "is_4k",

            "is_hd",

            "is_clean",

            "is_action",

            "is_clip",

            "is_cinematic",

            "is_gameplay",

            "is_dynamic",

            "has_music",

            "has_voice",

            "has_dialogue",

            "is_raw_footage",

            "is_no_music",

        ]



        for field in bool_fields:

            video[field] = bool(
                video.get(field,0)
            )



        video["views"] = int(
            video.get(
                "views",
                0
            )
            or 0
        )

        video["description"] = str(video.get("description", "") or "")
        video["music_confidence"] = str(video.get("music_confidence", "unknown") or "unknown")
        video["voice_confidence"] = str(video.get("voice_confidence", "unknown") or "unknown")
        video["dialogue_confidence"] = str(video.get("dialogue_confidence", "unknown") or "unknown")
        video["music_source"] = str(video.get("music_source", "metadata") or "metadata")
        video["voice_source"] = str(video.get("voice_source", "metadata") or "metadata")
        video["dialogue_source"] = str(video.get("dialogue_source", "metadata") or "metadata")



        video["score"] = float(
            video.get(
                "score",
                0
            )
            or 0
        )



        video["edit_score"] = float(
            video.get(
                "edit_score",
                0
            )
            or 0
        )



        results.append(
            video
        )



    return results