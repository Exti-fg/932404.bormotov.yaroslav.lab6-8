import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
import posts


class BlogApiTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "blog.sqlite"
        self.db_patch = patch("posts.DB_PATH", self.db_path)
        self.db_patch.start()
        posts.initialize()
        with posts.connect() as db:
            db.execute("DELETE FROM posts")
        self.client = TestClient(app)

    def tearDown(self):
        self.db_patch.stop()
        self.temp.cleanup()

    def test_post_crud_comments_and_cascade_delete(self):
        response = self.client.post(
            "/api/posts",
            json={"title": "Новая история", "content": "Подробный текст."},
        )
        self.assertEqual(response.status_code, 201)
        post = response.json()
        self.assertEqual(post["comments_count"], 0)

        comment_url = f"/api/posts/{post['id']}/comments"
        self.assertEqual(
            self.client.post(comment_url, json={"author": "   ", "text": "Привет"}).status_code,
            400,
        )
        comment = self.client.post(
            comment_url,
            json={"author": "Ира", "text": "Спасибо за историю!"},
        )
        self.assertEqual(comment.status_code, 201)
        self.assertEqual(len(self.client.get(comment_url).json()), 1)

        updated = self.client.put(
            f"/api/posts/{post['id']}",
            json={"title": "Обновлённая история", "content": "Новый текст."},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["title"], "Обновлённая история")
        self.assertEqual(updated.json()["comments_count"], 1)

        self.assertEqual(self.client.delete(f"/api/posts/{post['id']}").status_code, 204)
        self.assertEqual(self.client.get(f"/api/posts/{post['id']}").status_code, 404)
        self.assertEqual(self.client.get(comment_url).status_code, 404)

    def test_empty_database_stays_empty_after_initialization(self):
        posts.initialize()
        self.assertEqual(self.client.get("/api/posts").json()["total"], 0)

    def test_pagination_sorting_and_empty_content_validation(self):
        created = self.client.post(
            "/api/posts",
            json={"title": "Сортировка", "content": "Проверка страницы."},
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.client.get("/api/posts?limit=0").status_code, 400)
        self.assertEqual(
            self.client.post("/api/posts", json={"title": "   ", "content": "Текст"}).status_code,
            400,
        )
        self.assertEqual(
            self.client.post("/api/posts", json={"title": "Без текста", "content": "  "}).status_code,
            400,
        )
        result = self.client.get("/api/posts?page=1&limit=1&sort=asc").json()
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["limit"], 1)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["pages"], 1)
        self.assertEqual(len(result["items"]), 1)


if __name__ == "__main__":
    unittest.main()
