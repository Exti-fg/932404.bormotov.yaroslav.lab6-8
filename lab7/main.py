from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Path, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, StringConstraints

import orders

Status = Literal["new", "paid", "shipped", "delivered"]
OrderId = Annotated[int, Path(gt=0, le=2**63 - 1)]


class OrderCreate(BaseModel):
    customer_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    total_amount: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
    status: Status = "new"


class Order(OrderCreate):
    id: int


class StatusChange(BaseModel):
    status: Status


@asynccontextmanager
async def lifespan(app: FastAPI):
    orders.initialize()
    yield


app = FastAPI(title="Заказы", description="Лабораторная работа № 7", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    error = exc.errors()[0]
    field = str(error["loc"][-1])
    return JSONResponse(status_code=400, content={"detail": f"{field}: {error['msg']}"})


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/docs")


@app.get("/api/orders")
def get_orders(status: Status | None = None) -> list[Order]:
    return orders.list_orders(status)


@app.post("/api/orders", status_code=201, response_model=Order)
def post_order(body: OrderCreate):
    return orders.create_order(body.customer_name, body.total_amount, body.status)


@app.patch("/api/orders/{id}", response_model=Order)
def patch_order(id: OrderId, body: StatusChange):
    order = orders.change_status(id, body.status)
    if order is None:
        raise HTTPException(404, "Заказ не найден.")
    return order


@app.delete("/api/orders/{id}", status_code=204)
def remove_order(id: OrderId) -> Response:
    if not orders.delete_order(id):
        raise HTTPException(404, "Заказ не найден.")
    return Response(status_code=204)
