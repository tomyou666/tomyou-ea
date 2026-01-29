from fastapi import status
from fastapi.testclient import TestClient

from app_server.main import app
from app_server.routers import task_router

app.include_router(task_router.router)
client = TestClient(app)


def test_tasks():
    response = client.get("/tasktag/tasks/", headers={"X-Token": "coneofsilence"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"tasks": ["asdf"]}
