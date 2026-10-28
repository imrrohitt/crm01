"""
Central route definitions.
Single file where all routes are registered. Uses resources() and namespace().
Add your controllers and routes here.
"""

import asyncio
from contextlib import contextmanager
from typing import Callable, Iterator

from fastapi import APIRouter, FastAPI, HTTPException, Request, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from app.helpers.response_helper import error_response


def _wrap(
    controller_cls: type,
    action: str,
    handler: Callable,
    run_before: bool = True,
) -> Callable:
    """Run before_actions then call controller action. Return response."""

    async def _async_wrapper(
        request: Request,
        db: Session = Depends(get_db),
    ):
        request.state.path_params = getattr(request, "path_params", None) or {}
        ctrl = controller_cls(request=request, db=db)
        if request.headers.get("content-type", "").startswith("application/json"):
            await ctrl._get_body_json()
        try:
            if run_before:
                controller_cls._run_before_actions(ctrl, action)
        except HTTPException as e:
            return error_response(str(e.detail), code=e.status_code)
        except Exception as e:
            return error_response(str(e), code=500)
        result = handler(ctrl)
        if asyncio.iscoroutine(result):
            result = await result
        return controller_cls._run_after_actions(ctrl, action, result)

    return _async_wrapper


def resources(
    app_or_router: APIRouter | FastAPI,
    path: str,
    controller_cls: type,
    only: list[str] | None = None,
) -> None:
    """
    Register REST resource routes: index, show, create, update, destroy.
    GET path -> index, POST path -> create, GET path/{id} -> show, PUT path/{id} -> update, DELETE path/{id} -> destroy.
    """
    only = only or ["index", "show", "create", "update", "destroy"]
    if "index" in only:
        app_or_router.add_api_route(
            path,
            _wrap(controller_cls, "index", lambda c: c.index()),
            methods=["GET"],
        )
    if "create" in only:
        app_or_router.add_api_route(
            path,
            _wrap(controller_cls, "create", lambda c: c.create()),
            methods=["POST"],
        )
    if "show" in only:
        app_or_router.add_api_route(
            f"{path}/{{id:int}}",
            _wrap(controller_cls, "show", lambda c: c.show()),
            methods=["GET"],
        )
    if "update" in only:
        app_or_router.add_api_route(
            f"{path}/{{id:int}}",
            _wrap(controller_cls, "update", lambda c: c.update()),
            methods=["PUT"],
        )
    if "destroy" in only:
        app_or_router.add_api_route(
            f"{path}/{{id:int}}",
            _wrap(controller_cls, "destroy", lambda c: c.destroy()),
            methods=["DELETE"],
        )


@contextmanager
def namespace(app: FastAPI, prefix: str) -> Iterator[APIRouter]:
    """Context manager: yield a router with prefix, then include it in app."""
    router = APIRouter(prefix=prefix)
    yield router
    app.include_router(router)


def draw_routes(app: FastAPI) -> None:
    """
    Register all routes. Framework only — add your resources here.
    Example:
        with namespace(app, "/api/v1") as router:
            resources(router, "/articles", ArticlesController)
    """
    # No application routes by default — add your controllers above
    pass
