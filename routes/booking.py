from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response
import mysql.connector
from pydantic import BaseModel
import shutil
import os
import random
import requests
import dotenv
from pathlib import Path

dotenv.load_dotenv(Path(__file__).resolve().parents[2] / ".env")

EMAIL_API_KEY = os.getenv("EMAIL_API_KEY", "")

app = FastAPI()

otp_storage = {}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# images folder
os.makedirs("images", exist_ok=True)

app.mount(
    "/images",
    StaticFiles(directory=Path(__file__).resolve().parents[2] / "images"),
    name="images"
)

@app.get("/", response_class=JSONResponse)
def root():
    return {"status": "ok", "message": "Booking API is running"}

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

# -------- DB CONNECT --------
def get_db():

    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="@Ashish911",
        database="testdb",
        autocommit=True
    )

# -------- MODELS --------
class User(BaseModel):
    email: str
    password: str

class VerifyOTP(BaseModel):
    email: str
    password: str
    otp: str

class CartItem(BaseModel):
    user_id: int
    product_id: int

class Product(BaseModel):
    name: str
    price: int
    description: str

class ProductImage(BaseModel):
    product_id: int
    image_url: str

class Order(BaseModel):
    user_id: int
    product_id: int
    product: str
    name: str
    phone: str
    address: str

class EmailOrder(BaseModel):
    product: str
    name: str
    phone: str
    address: str

# ================= SEND OTP =================
@app.post("/send-otp")
def send_otp(user: User):

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=%s",
        (user.email,)
    )

    if cursor.fetchone():

        return {
            "success": False,
            "message": "User already exists"
        }

    otp = str(random.randint(100000,999999))

    otp_storage[user.email] = {
        "otp": otp,
        "password": user.password
    }

    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "accept": "application/json",
        "api-key": EMAIL_API_KEY,
        "content-type": "application/json"
    }

    data = {

        "sender": {
            "name": "Shop",
            "email": "ashishpandeypro705@gmail.com"
        },

        "to": [
            {
                "email": user.email
            }
        ],

        "subject": "OTP Verification",

        "htmlContent": f"""
        <h1>Your OTP</h1>
        <h2>{otp}</h2>
        """
    }

    requests.post(
        url,
        json=data,
        headers=headers
    )

    return {
        "success": True,
        "message": "OTP sent"
    }

# ================= VERIFY OTP =================
@app.post("/verify-otp")
def verify_otp(data: VerifyOTP):

    if data.email not in otp_storage:

        return {
            "success": False,
            "message": "OTP expired"
        }

    saved = otp_storage[data.email]

    if saved["otp"] != data.otp:

        return {
            "success": False,
            "message": "Wrong OTP"
        }

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "INSERT INTO users (email,password) VALUES (%s,%s)",
        (
            data.email,
            saved["password"]
        )
    )

    del otp_storage[data.email]

    return {
        "success": True,
        "message": "Signup successful"
    }

# ================= LOGIN =================
@app.post("/login")
def login(user: User):

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT id,password FROM users WHERE email=%s",
        (user.email,)
    )

    u = cursor.fetchone()

    if not u:

        return {
            "success": False,
            "message": "User not found"
        }

    if u[1].strip() != user.password.strip():

        return {
            "success": False,
            "message": "Wrong password"
        }

    return {
        "success": True,
        "user_id": u[0]
    }

# ================= CART =================
@app.post("/add-to-cart")
def add_to_cart(item: CartItem):

    db = get_db()
    cursor = db.cursor()

    try:

        cursor.execute(
            "INSERT INTO cart (user_id,product_id,quantity) VALUES (%s,%s,1)",
            (item.user_id, item.product_id)
        )

        return {"message": "Added"}

    except Exception as e:

        print("CART ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# ================= IMAGE UPLOAD =================
@app.post("/upload-image")
def upload_image(file: UploadFile = File(...)):

    try:

        filename = file.filename

        path = f"images/{filename}"

        with open(path, "wb") as buffer:

            shutil.copyfileobj(file.file, buffer)

        url = f"http://127.0.0.1:8000/images/{filename}"

        return {"url": url}

    except Exception as e:

        print("UPLOAD ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# ================= ADD PRODUCT =================
@app.post("/add-product")
def add_product(product: Product):

    db = get_db()
    cursor = db.cursor()

    try:

        cursor.execute(
            "INSERT INTO products (name,price,description) VALUES (%s,%s,%s)",
            (
                product.name,
                product.price,
                product.description
            )
        )

        pid = cursor.lastrowid

        return {"product_id": pid}

    except Exception as e:

        print("PRODUCT ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# ================= LINK IMAGE =================
@app.post("/add-product-image")
def add_product_image(data: ProductImage):

    db = get_db()
    cursor = db.cursor()

    if not data.image_url:

        raise HTTPException(
            status_code=400,
            detail="Image URL missing"
        )

    try:

        cursor.execute(
            "INSERT INTO product_images (product_id,image_url) VALUES (%s,%s)",
            (
                data.product_id,
                data.image_url
            )
        )

        return {"success": True}

    except Exception as e:

        print("IMAGE LINK ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# ================= GET PRODUCTS =================
@app.get("/products")
def get_products():

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM products")

    products = cursor.fetchall()

    result = []

    for p in products:

        pid = p[0]

        cursor.execute(
            "SELECT image_url FROM product_images WHERE product_id=%s",
            (pid,)
        )

        imgs = cursor.fetchall()

        result.append({
            "id": pid,
            "name": p[1],
            "price": p[2],
            "desc": p[3],
            "images": [i[0] for i in imgs]
        })

    return result

# ================= PLACE ORDER =================
@app.post("/place-order")
def place_order(order: Order):

    db = get_db()
    cursor = db.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO orders
            (user_id, product_id, customer_name, phone, address)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (
                order.user_id,
                order.product_id,
                order.name,
                order.phone,
                order.address
            )
        )

        return {
            "success": True,
            "message": "Order placed"
        }

    except Exception as e:

        print("ORDER ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# ================= SEND ORDER EMAIL =================
@app.post("/send-order-email")
def send_order_email(data: EmailOrder):

    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "accept": "application/json",
        "api-key": "REDACTED_EMAIL_API_KEY",
        "content-type": "application/json"
    }

    html = f"""
    <h1>New Order</h1>

    <p><b>Product:</b> {data.product}</p>

    <p><b>Name:</b> {data.name}</p>

    <p><b>Phone:</b> {data.phone}</p>

    <p><b>Address:</b> {data.address}</p>
    """

    body = {

        "sender": {
            "name": "Shop",
            "email": "ashishpandeypro705@gmail.com"
        },

        "to": [
            {
                "email": "ashishpandeypro705@gmail.com"
            }
        ],

        "subject": "New Order Received",

        "htmlContent": html
    }

    requests.post(
        url,
        json=body,
        headers=headers
    )

    return {
        "success": True
    }

# ================= USER ORDER HISTORY =================
@app.get("/my-orders/{user_id}")
def my_orders(user_id: int):

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT
        orders.id,
        products.name,
        products.price,
        products.description,
        orders.phone,
        orders.address,
        orders.created_at,
        products.id

        FROM orders

        JOIN products
        ON orders.product_id = products.id

        WHERE orders.user_id=%s

        ORDER BY orders.id DESC
    """, (user_id,))

    rows = cursor.fetchall()

    result = []

    for row in rows:

        product_id = row[7]

        cursor.execute(
            "SELECT image_url FROM product_images WHERE product_id=%s",
            (product_id,)
        )

        imgs = cursor.fetchall()

        result.append({
            "order_id": row[0],
            "product_name": row[1],
            "price": row[2],
            "description": row[3],
            "phone": row[4],
            "address": row[5],
            "created_at": str(row[6]),
            "images": [i[0] for i in imgs]
        })

    return result