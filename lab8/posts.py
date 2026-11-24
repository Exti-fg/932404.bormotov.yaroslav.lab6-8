import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).with_name("blog.sqlite")


@contextmanager
def connect():
    with closing(sqlite3.connect(DB_PATH)) as db, db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        yield db


def initialize():
    with connect() as db:
        is_new_database = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'posts'"
        ).fetchone() is None
        db.executescript("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 120),
                content TEXT NOT NULL CHECK (length(trim(content)) BETWEEN 1 AND 10000),
                published_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY,
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                author TEXT NOT NULL CHECK (length(trim(author)) BETWEEN 1 AND 80),
                text TEXT NOT NULL CHECK (length(trim(text)) BETWEEN 1 AND 2000),
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS comments_post_id_idx ON comments(post_id);
            CREATE INDEX IF NOT EXISTS posts_published_at_idx ON posts(published_at);
        """)
        if is_new_database:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            examples = (
                (
                    "Заметки о цифровом минимализме",
                    "Иногда лучший способ успеть больше — убрать лишнее. Я начал с уведомлений: оставил только действительно важные, а для чтения и работы выделил отдельное время. Результат оказался заметнее, чем ожидал.",
                ),
                (
                    "Город, который просыпается раньше",
                    "Утренние прогулки открывают знакомые улицы с другой стороны. Пекарни только включают свет, трамваи идут почти пустыми, а в парке слышны птицы. Собрал несколько маршрутов для тех, кому тоже нравится тихое начало дня.",
                ),
                (
                    "Как я учусь новому без спешки",
                    "Небольшие регулярные шаги работают лучше редких марафонов. Сейчас я уделяю новому навыку по двадцать минут в день, записываю вопросы и раз в неделю возвращаюсь к заметкам. Этот блог — место, где буду делиться такими наблюдениями.",
                ),
            )
            db.executemany(
                "INSERT INTO posts (title, content, published_at) VALUES (?, ?, ?)",
                ((title, content, now) for title, content in examples),
            )


def _post_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "published_at": row["published_at"],
        "comments_count": row["comments_count"],
    }


def list_posts(page: int, limit: int, sort: str) -> dict:
    direction = "ASC" if sort == "asc" else "DESC"
    offset = (page - 1) * limit
    with connect() as db:
        total = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        rows = db.execute(
            f"""
            SELECT p.*, COUNT(c.id) AS comments_count
            FROM posts p
            LEFT JOIN comments c ON c.post_id = p.id
            GROUP BY p.id
            ORDER BY p.published_at {direction}, p.id {direction}
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    return {
        "items": [_post_dict(row) for row in rows],
        "page": page,
        "limit": limit,
        "total": total,
        "pages": (total + limit - 1) // limit,
    }


def get_post(post_id: int) -> dict | None:
    with connect() as db:
        row = db.execute(
            """
            SELECT p.*, COUNT(c.id) AS comments_count
            FROM posts p LEFT JOIN comments c ON c.post_id = p.id
            WHERE p.id = ?
            GROUP BY p.id
            """,
            (post_id,),
        ).fetchone()
    return _post_dict(row) if row else None


def create_post(title: str, content: str) -> dict:
    published_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO posts (title, content, published_at) VALUES (?, ?, ?)",
            (title, content, published_at),
        )
    return get_post(cursor.lastrowid)


def update_post(post_id: int, title: str, content: str) -> dict | None:
    with connect() as db:
        cursor = db.execute(
            "UPDATE posts SET title = ?, content = ? WHERE id = ?",
            (title, content, post_id),
        )
    return get_post(post_id) if cursor.rowcount else None


def delete_post(post_id: int) -> bool:
    with connect() as db:
        return db.execute("DELETE FROM posts WHERE id = ?", (post_id,)).rowcount > 0


def list_comments(post_id: int) -> list[dict] | None:
    with connect() as db:
        if db.execute("SELECT 1 FROM posts WHERE id = ?", (post_id,)).fetchone() is None:
            return None
        rows = db.execute(
            "SELECT id, post_id, author, text, created_at FROM comments "
            "WHERE post_id = ? ORDER BY created_at ASC, id ASC",
            (post_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_comment(post_id: int, author: str, text: str) -> dict | None:
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as db:
        if db.execute("SELECT 1 FROM posts WHERE id = ?", (post_id,)).fetchone() is None:
            return None
        cursor = db.execute(
            "INSERT INTO comments (post_id, author, text, created_at) VALUES (?, ?, ?, ?)",
            (post_id, author, text, created_at),
        )
        row = db.execute(
            "SELECT id, post_id, author, text, created_at FROM comments WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row)
