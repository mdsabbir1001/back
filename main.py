import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from supabase import create_client, Client
from fastapi.middleware.cors import CORSMiddleware # Ei line ta add korun

import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

app = FastAPI()

# Ei block ta add korun
origins = [
    "http://localhost:5173", # Jodi local e test koren
    "https://your-github-username.github.io", # Apnar GitHub Pages URL (ETA CHANGE KORUN)
    # Aro onno kono frontend URL thakle add korte paren
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

class UserCredentials(BaseModel):
    email: str
    password: str

class Content(BaseModel):
    key: str
    value: str

class Image(BaseModel):
    name: str
    url: str
    alt_text: str | None = None

class Message(BaseModel):
    name: str
    email: str
    subject: str | None = None
    message: str

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/signup")
def signup(credentials: UserCredentials):
    try:
        # Supabase Auth e user toiri korchi
        auth_response = supabase.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password,
        })

        # Ekhon 'users' table e notun user er data insert korchi
        # Jodio Supabase Auth nijer table e user rakhe, 
        # amra 'role' manage korar jonno nijeder table o use korbo.
        
        # Auth theke user er ID ta nicchi
        user_id = auth_response.user.id
        
        # 'users' table e data insert korchi
        table_response, count = supabase.table('users').insert({
            "id": user_id,
            "email": credentials.email,
            # By default role 'user' set hobe, jodi na amra alada kichu boli
        }).execute()

        return {"message": "User created successfully", "user_id": user_id}

    except Exception as e:
        # Jodi kono error hoy, jemon user already ache
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/login")
def login(credentials: UserCredentials):
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password,
        })
        return {"message": "Login successful", "user": auth_response.user.email, "access_token": auth_response.session.access_token}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

# Content Management Endpoints
@app.get("/content/{key}")
async def get_content(key: str):
    try:
        response, count = supabase.table('contents').select("*").eq("key", key).single().execute()
        if response[1]:
            return response[1]
        raise HTTPException(status_code=404, detail="Content not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/content")
async def create_content(content: Content):
    try:
        response, count = supabase.table('contents').insert(content.dict()).execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/content/{key}")
async def update_content(key: str, content: Content):
    try:
        response, count = supabase.table('contents').update(content.dict()).eq("key", key).execute()
        if response[1]:
            return response[1]
        raise HTTPException(status_code=404, detail="Content not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Image Management Endpoints
@app.post("/images/upload")
async def upload_image(file: UploadFile = File(...), name: str = None, alt_text: str | None = None):
    try:
        if not name:
            name = file.filename

        # Upload to Supabase Storage
        file_content = await file.read()
        path = f"public/{name}"
        storage_response = supabase.storage.from_("images").upload(path, file_content, {"content-type": file.content_type})

        # Get public URL
        public_url = supabase.storage.from_("images").get_public_url(path)

        # Save metadata to database
        image_data = {"name": name, "url": public_url, "alt_text": alt_text}
        response, count = supabase.table('images').insert(image_data).execute()
        return {"message": "Image uploaded successfully", "url": public_url, "data": response[1]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images/{name}")
async def get_image(name: str):
    try:
        response, count = supabase.table('images').select("*").eq("name", name).single().execute()
        if response[1]:
            return response[1]
        raise HTTPException(status_code=404, detail="Image not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/images/{name}")
async def delete_image(name: str):
    try:
        # Delete from Supabase Storage
        storage_response = supabase.storage.from_("images").remove([f"public/{name}"])

        # Delete metadata from database
        response, count = supabase.table('images').delete().eq("name", name).execute()
        if response[1]:
            return {"message": "Image deleted successfully"}
        raise HTTPException(status_code=404, detail="Image not found in database")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Message Management Endpoints
@app.post("/messages")
async def create_message(message: Message):
    try:
        response, count = supabase.table('messages').insert(message.dict()).execute()
        return {"message": "Message sent successfully", "data": response[1]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/messages")
async def get_all_messages():
    try:
        response, count = supabase.table('messages').select("*").order("received_at", desc=True).execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/messages/{message_id}/read")
async def mark_message_as_read(message_id: str):
    try:
        response, count = supabase.table('messages').update({"is_read": True}).eq("id", message_id).execute()
        if response[1]:
            return {"message": "Message marked as read", "data": response[1]}
        raise HTTPException(status_code=404, detail="Message not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
