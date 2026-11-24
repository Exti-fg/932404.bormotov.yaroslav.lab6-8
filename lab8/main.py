from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Path as PathParam, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, StringConstraints

import posts

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

PostId = Annotated[int, PathParam(gt=0, le=2**63 - 1)]
PostTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
PostContent = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
Author = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
CommentText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class PostInput(BaseModel):
    title: PostTitle
    content: PostContent


class CommentInput(BaseModel):
    author: Author
    text: CommentText


@asynccontextmanager
async def lifespan(app: FastAPI):
    posts.initialize()
    yield


app = FastAPI(
    title="Листья — блог с комментариями",
    description="Лабораторная работа № 8 — итоговый мини-проект",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    error = exc.errors()[0]
    field = str(error["loc"][-1])
    return JSONResponse(status_code=400, content={"detail": f"{field}: {error['msg']}"})


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/posts")
def get_posts(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=12)] = 6,
    sort: Literal["asc", "desc"] = "desc",
) -> dict:
    return posts.list_posts(page, limit, sort)


@app.get("/api/posts/{post_id}")
def get_post(post_id: PostId) -> dict:
    post = posts.get_post(post_id)
    if post is None:
        raise HTTPException(404, "Пост не найден.")
    return post


@app.post("/api/posts", status_code=201)
def post_post(body: PostInput) -> dict:
    return posts.create_post(body.title, body.content)


@app.put("/api/posts/{post_id}")
def put_post(post_id: PostId, body: PostInput) -> dict:
    post = posts.update_post(post_id, body.title, body.content)
    if post is None:
        raise HTTPException(404, "Пост не найден.")
    return post


@app.delete("/api/posts/{post_id}", status_code=204)
def remove_post(post_id: PostId) -> Response:
    if not posts.delete_post(post_id):
        raise HTTPException(404, "Пост не найден.")
    return Response(status_code=204)


@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id: PostId) -> list[dict]:
    comments = posts.list_comments(post_id)
    if comments is None:
        raise HTTPException(404, "Пост не найден.")
    return comments


@app.post("/api/posts/{post_id}/comments", status_code=201)
def post_comment(post_id: PostId, body: CommentInput) -> dict:
    comment = posts.create_comment(post_id, body.author, body.text)
    if comment is None:
        raise HTTPException(404, "Пост не найден.")
    return comment
