import json
import os
import sqlite3
from contextlib import contextmanager
from enum import Enum

from dotenv import load_dotenv
from loguru import logger

load_dotenv()
dbdatapath = os.path.join(os.getcwd(), os.environ.get("DBDATAPATH"))


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

    create_usertable_sql = """
    CREATE TABLE IF NOT EXISTS discordusers (
        author_id INTEGER PRIMARY KEY,
        author_nickname TEXT,
        author_name TEXT
    ) ;  
    """
    if not os.path.exists(os.path.dirname(dbdatapath)):
        os.makedirs(os.path.dirname(dbdatapath))
    with sqlite_connection() as cursor:
        # Execute the SQL command
        cursor.execute(create_table_sql)
        cursor.execute(create_usertable_sql)


def upsert_message_stats(
    ogmessage_id: int, roundness: float, labels_json: dict
) -> None:
    logger.info(f"Upserting: {ogmessage_id}, {roundness}, {labels_json} in messages")
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


def upsert_user_info(author_id: int, author_nickname: str, author_name: str):
    # Inserts the author info to cache results so we don't have to get info from discord all the time
    logger.info(
        f"Upserting: {author_id}, {author_nickname}, {author_name} in discordusers"
    )
    # Convert the labels_json dictionary to a JSON string
    # Define the UPSERT SQL command
    upsert_sql = """
    INSERT INTO discordusers (author_id, author_nickname, author_name)
    VALUES (?, ?, ?)
    ON CONFLICT(author_id) DO UPDATE SET
        author_nickname=excluded.author_nickname,
        author_name=excluded.author_name
    """

    with sqlite_connection() as cursor:
        cursor.execute(upsert_sql, (author_id, author_nickname, author_name))


def select_user_info(author_id: int):
    logger.trace(f"Getting user info from {author_id}")
    select_sql = "SELECT author_id, author_nickname, author_name FROM discordusers WHERE author_id = ?"
    with sqlite_connection() as cursor:
        cursor.execute(select_sql, (author_id,))
        row = cursor.fetchone()
        if row:
            return {
                "author_id": row[0],
                "author_nickname": row[1],
                "author_name": row[2],
            }
        return None


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


class OrderBy(Enum):
    ASC = "ASC"
    DES = "DESC"


def get_minmax_roundness_byuserid(user_id: int, orderby: OrderBy) -> dict:
    # Returns min and max roundness of specified user, returning the ogmessage_id and jump_url as well
    logger.info(f"Fetching min and max roundness for user_id: {user_id}")

    # Define the SQL query to fetch min and max roundness, ogmessage_id, and jump_url
    query = f"""
    SELECT roundness, ogmessage_id, replymessage_jump_url
    FROM messages
    WHERE author_id = ?
    ORDER BY roundness {orderby}, ogmessage_id {orderby}
    """

    result = {
        "roundness": None,
        "roundness_url": None,
        "roundness_ogmessage_id": None,
    }

    with sqlite_connection() as cursor:
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        if rows:
            result["roundness"] = rows[0][0]
            result["roundness_ogmessage_id"] = rows[0][1]
            result["roundness_url"] = rows[0][2]
    return result


def get_minmax_roundness_leaderboard(n: int, orderby: OrderBy) -> dict:
    # Returns top 'n' min and max roundness returning the ogmessage_id and jump_url as well for each row
    logger.info(f"Fetching min and max roundness top {n} leaderboard")

    # Define the SQL queries to fetch top 'n' min and max roundness, ogmessage_id, and jump_url
    roundness_query = f"""
    SELECT roundness, ogmessage_id, replymessage_jump_url, author_id, guild_id, channel_id
    FROM messages
    WHERE roundness not null
    ORDER BY roundness {orderby}
    LIMIT ?
    """

    result = []

    with sqlite_connection() as cursor:
        cursor.execute(roundness_query, (n,))
        min_rows = cursor.fetchall()
        for row in min_rows:
            result.append(
                {
                    "roundness": row[0],
                    "ogmessage_id": row[1],
                    "jump_url": row[2],
                    "author_id": row[3],
                    "guild_id": row[4],
                    "channel_id": row[5],
                }
            )
    return result


if __name__ == "__main__":
    # create db
    # create_db()
    res = get_minmax_roundness_leaderboard(3, OrderBy.DES.value)
    # res = select_user_info(123)
    a = 5
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
