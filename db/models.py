import json
import os
import sqlite3
from contextlib import contextmanager

import discord
from loguru import logger

# Connect to the SQLite database (or create it if it doesn't exist)

dbdatapath = os.path.join("dbdata", "messages.db")


@contextmanager
def sqlite_connection(db_path=dbdatapath):
    conn = None
    cursor = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def create_db() -> None:
    # Define the SQL command to create the "messages" table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS messages (
        ogmessage_id INTEGER PRIMARY KEY,
        replymessage_jump_url TEXT,
        replymessage_id INTEGER,
        author_id INTEGER,
        channel_id INTEGER,
        guild_id INTEGER,
        roundness REAL,
        labels_json TEXT
    )
    """
    with sqlite_connection() as cursor:
        # Execute the SQL command
        cursor.execute(create_table_sql)


def upsert_message_stats(
    ogmessage_id: int, roundness: float, labels_json: dict
) -> None:
    logger.info(f"Upserting: {ogmessage_id}, {roundness}, {labels_json}")
    # Convert the labels_json dictionary to a JSON string
    labels_json_str = json.dumps(labels_json)

    # Define the UPSERT SQL command
    upsert_sql = """
    INSERT INTO messages (ogmessage_id, roundness, labels_json)
    VALUES (?, ?, ?)
    ON CONFLICT(ogmessage_id) DO UPDATE SET
        roundness=excluded.roundness,
        labels_json=excluded.labels_json
    """

    with sqlite_connection() as cursor:
        cursor.execute(upsert_sql, (ogmessage_id, roundness, labels_json_str))


def upsert_message_discordinfo(
    ogmessage_id: int,
    replymessage_jump_url: str,
    replymessage_id: int,
    author_id: int,
    channel_id: int,
    guild_id: int,
) -> None:
    logger.info(
        f"Upserting: {ogmessage_id}, {replymessage_jump_url}, {replymessage_id}, {author_id}, {channel_id}, {guild_id}"
    )
    # Define the UPSERT SQL command
    upsert_sql = """
    INSERT INTO messages (ogmessage_id, replymessage_jump_url, replymessage_id, author_id, channel_id, guild_id)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(ogmessage_id) DO UPDATE SET
        replymessage_jump_url=excluded.replymessage_jump_url,
        replymessage_id=excluded.replymessage_id,
        author_id=excluded.author_id,
        channel_id=excluded.channel_id,
        guild_id=excluded.guild_id
    """

    with sqlite_connection() as cursor:
        cursor.execute(
            upsert_sql,
            (
                ogmessage_id,
                replymessage_jump_url,
                replymessage_id,
                author_id,
                channel_id,
                guild_id,
            ),
        )


def get_minmax_roundness_byuserid(user_id: int) -> dict:
    # Returns min and max roundness of specified user, returning the ogmessage_id and jump_url as well
    logger.info(f"Fetching min and max roundness for user_id: {user_id}")

    # Define the SQL query to fetch min and max roundness, ogmessage_id, and jump_url
    query = """
    SELECT roundness, ogmessage_id, replymessage_jump_url
    FROM messages
    WHERE author_id = ?
    ORDER BY roundness ASC, ogmessage_id ASC
    """

    # Define the SQL query to fetch min and max roundness, ogmessage_id, and jump_url
    query = """
    SELECT roundness, ogmessage_id, replymessage_jump_url
    FROM messages
    WHERE author_id = ?
    ORDER BY roundness ASC, ogmessage_id ASC
    """

    result = {
        "min_roundness": None,
        "max_roundness": None,
        "min_roundness_url": None,
        "max_roundness_url": None,
        "min_roundness_ogmessage_id": None,
        "max_roundness_ogmessage_id": None,
    }

    with sqlite_connection() as cursor:
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        if rows:
            result["min_roundness"] = rows[0][0]
            result["min_roundness_ogmessage_id"] = rows[0][1]
            result["min_roundness_url"] = rows[0][2]

            result["max_roundness"] = rows[-1][0]
            result["max_roundness_ogmessage_id"] = rows[-1][1]
            result["max_roundness_url"] = rows[-1][2]

    return result


if __name__ == "__main__":
    # create db
    create_db()
    """
    ogmessageid = 231231
    upsert_message_stats(
        ogmessageid,
        None,
        {
            "bread": 0.80332,
            "oblong": 0.68173,
            "no_seeds": 0.33406,
            "raised": 0.31631,
            "white": 0.22345,
            "cooked": 0.13072,
            "round": 0.11216,
            "baguette": 0.05641,
        },
    )
    upsert_message_discordinfo(
        ogmessageid, "http://google.com", 123214, 12313, 13213, 123123
    )
    res = get_minmax_roundness_byuserid(206734328879775746)
    a = 5
"""
