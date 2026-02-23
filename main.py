from fastapi import FastAPI
from fastapi.params import Depends

from routes import auth, carts, movies, orders, payments, stripe_webhook
from schemas.users import UserReadSchema
from src.services.users import get_current_user

app = FastAPI()


@app.get("/me")
def me(current_user: UserReadSchema = Depends(get_current_user)):
    return current_user


app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(carts.router)

app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(stripe_webhook.router)
