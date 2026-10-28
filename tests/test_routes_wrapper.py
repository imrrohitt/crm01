"""Tests for the route wrapper: resources(), namespace(), params, auth errors, after_action."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.controllers.base_controller import BaseController, after_action, before_action
from app.controllers.concerns.authenticatable import Authenticatable
from config.routes import namespace, resources


class ThingsController(Authenticatable, BaseController):
    @before_action(only=["create"])
    def need_auth(self) -> None:
        self.authenticate_user()

    @after_action
    def tag(self, response):
        response.headers["X-After"] = "1"
        return response

    def index(self):
        return self.render_json({"params": self.params})

    def show(self):
        return self.render_json(self.params)

    def create(self):
        return self.render_json(self.params, status=201)


@pytest.fixture
def wrapped_client() -> TestClient:
    app = FastAPI()
    with namespace(app, "/api/v1") as router:
        resources(router, "/things", ThingsController, only=["index", "show", "create"])
    return TestClient(app)


def test_namespace_and_path_param(wrapped_client: TestClient) -> None:
    r = wrapped_client.get("/api/v1/things/7")
    assert r.status_code == 200
    assert r.json()["data"] == {"id": 7}


def test_params_merge_query_and_json_body(wrapped_client: TestClient) -> None:
    r = wrapped_client.get("/api/v1/things?page=2")
    assert r.json()["data"]["params"] == {"page": "2"}


def test_before_action_http_exception_keeps_status(wrapped_client: TestClient) -> None:
    r = wrapped_client.post("/api/v1/things", json={"name": "x"})
    assert r.status_code == 401
    assert r.json()["success"] is False


def test_after_action_runs(wrapped_client: TestClient) -> None:
    r = wrapped_client.get("/api/v1/things")
    assert r.headers.get("X-After") == "1"
