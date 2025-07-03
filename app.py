import pyrebase
import uvicorn
from functools import wraps
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import User
from typing_extensions import MutableMapping
from dotenv import load_dotenv
import os
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from authlib.integrations.starlette_client import OAuth, OAuthError

load_dotenv()

MIDDLEWARE_SECRET_KEY = os.environ.get("MIDDLEWARE_SECRET_KEY", None)
CLIENT_ID = os.environ.get("CLIENT_ID", None)
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", None)
apiKey = os.environ.get("apiKey", None)
authDomain = os.environ.get("authDomain", None)
projectId = os.environ.get("projectId", None)
databaseURL = os.environ.get("databaseURL", None)
storageBucket = os.environ.get("storageBucket", None)
messagingSenderId = os.environ.get("messagingSenderId", None)
appId = os.environ.get("appId", None)
measurementId = os.environ.get("measurementId", None)
serviceAccount = os.environ.get("serviceAccount", None)

firebaseConfig = {
    'apiKey': apiKey,
    'authDomain': authDomain,
    'projectId': projectId,
    'databaseURL': databaseURL,
    'storageBucket': storageBucket,
    'messagingSenderId': messagingSenderId,
    'appId': appId,
    'measurementId': measurementId,
    "serviceAccount": serviceAccount,
}

firebase = pyrebase.initialize_app(firebaseConfig)
firebase_auth = firebase.auth()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["*"] during dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=MIDDLEWARE_SECRET_KEY)



oauth = OAuth()
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    client_kwargs={
        'scope': 'email openid profile',
        'redirect_uri': 'http://localhost:8000/auth'
    }
)

def login_required(fn):
    @wraps(fn)
    async def wrapper(request: Request, *args, **kwargs):
        user = request.session.get("user")
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        # pass the request (and any other args) through to the actual endpoint
        return await fn(request, *args, **kwargs)
    return wrapper

@app.get("/health")
async def root():
    return {"message": "Health Check: Server is running!"}

@app.get("/")
async def index(request: Request):
    try:
        user = request.session.get('user')
        if user:
            return {
                "message": f"Welcome {user['email']}!",
                "status": "success"
            }

        return {
            "message": "Welcome to the Meme Generator!",
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/login")
async def login(body: User, request: Request):
    try:
        user = firebase_auth.sign_in_with_email_and_password(body.email, body.password.get_secret_value())
        print(f"User {user} logged in successfully thru email and firebase")
        request.session["user"] = {
            "email": body.email,
            "idToken": user["idToken"],
            # you can also store fb_user["refreshToken"] if you want to refresh later
        }
        return {
            "status": "success",
            "response": "User Logged in successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/register")
async def register(body: User):
    try:
        user = firebase_auth.create_user_with_email_and_password(body.email, body.password.get_secret_value())
        return {
            "status": "success",
            "response": "User created successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

# Check if the user is authenticated for protected area
@app.get('/welcome')
@login_required
async def welcome(request: Request):
    user = request.session.get('user')
    if not user:
        return HTTPException(status_code=401, detail="User not authenticated")
    return {
        "message": f"Welcome {user}!",
        "status": "success"
    }

@app.get("/google_login")
async def googlelogin(request: Request):
    url = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, url)

@app.get('/auth')
async def auth(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as e:
        return HTTPException(status_code=400, detail=str(e))
    user = token.get('userinfo')
    if user:
        request.session['user'] = dict(user)
        print(f"User {user} logged in successfully")
    return {
        "message": f"Welcome {user['email']}!",
        "status": "success"
    }

@app.get('/logout')
async def logout(request: Request):
    request.session.pop('user')
    request.session.clear()
    return {
        "message": "User logged out successfully",
        "status": "success"
    }

@app.get("/protected-data")
@login_required
async def protected_data(request: Request):
    user = request.session["user"]
    return {"secret_data": "🕵️‍♂️ only for " + user["email"]}

if __name__ == "__main__":
    uvicorn.run(
        app="app:app",
        host="localhost",
        port=8000,
        reload=True
    )