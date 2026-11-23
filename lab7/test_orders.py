import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


class OrdersTest(unittest.TestCase):
    def test_order_lifecycle(self):
        url = "/api/orders"
        with TemporaryDirectory() as tmp, patch("orders.DB_PATH", Path(tmp) / "orders.sqlite"):
            with TestClient(app) as client:
                body = {"customer_name": "Анна", "total_amount": 0}
                self.assertEqual(client.post(url, json={**body, "total_amount": -1}).status_code, 400)
                created = client.post(url, json=body)
                self.assertEqual(created.status_code, 201)
                order = created.json()
                self.assertEqual(order, {**body, "id": order["id"], "status": "new"})
                item = f"{url}/{order['id']}"
                self.assertEqual(client.patch(item, json={"status": "unknown"}).status_code, 400)
                self.assertEqual(client.get(url, params={"status": "paid"}).json(), [])
                paid = {**order, "status": "paid"}
                self.assertEqual(client.patch(item, json={"status": "paid"}).json(), paid)
            with TestClient(app) as client:
                self.assertEqual(client.get(url, params={"status": "paid"}).json(), [paid])
                self.assertEqual(client.delete(item).status_code, 204)
                self.assertEqual(client.get(url).json(), [])
                self.assertEqual(client.delete(item).status_code, 404)
