import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from supabase import create_client, Client
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import json

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

app = FastAPI()

origins = [
    "http://localhost:5173",
    "https://minimindcreatives.netlify.app",
    "https://adminminimind.netlify.app",
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

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_response.user.dict()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

# --- Pydantic Models ---

class UserCredentials(BaseModel):
    email: str
    password: str

class Content(BaseModel):
    key: str
    value: str

class Message(BaseModel):
    name: str
    email: str
    subject: Optional[str] = None
    message: str

class TeamMember(BaseModel):
    name: str
    designation: str
    image_url: str
    bio: Optional[str] = None
    specialties: Optional[List[str]] = None
    social_url_a: Optional[str] = None
    social_url_b: Optional[str] = None
    social_url_c: Optional[str] = None

class PortfolioCategory(BaseModel):
    name: str

class PortfolioProject(BaseModel):
    title: str
    description: str
    image_url: str
    category_id: int

class Service(BaseModel):
    title: str
    description: str
    icon: str
    price: Optional[str] = None
    features: List[str]
    cover_image_url: Optional[str] = None

# --- Root ---

@app.get("/")
def read_root():
    return {"Hello": "Minimind API"}

# --- Auth Endpoints ---

@app.post("/signup")
def signup(credentials: UserCredentials):
    try:
        auth_response = supabase.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password,
        })
        user_id = auth_response.user.id
        supabase.table('users').insert({"id": user_id, "email": credentials.email}).execute()
        return {"message": "User created successfully", "user_id": user_id}
    except Exception as e:
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

# --- Content Management ---

@app.get("/content/{key}")
async def get_content(key: str):
    try:
        response, count = supabase.table('contents').select("*").eq("key", key).single().execute()
        if response[1]:
            content_data = response[1]
            if 'value' in content_data and content_data['value']:
                try:
                    parsed_value = json.loads(content_data['value'])
                    if 'featuredServices' not in parsed_value or not isinstance(parsed_value['featuredServices'], list):
                        parsed_value['featuredServices'] = []
                    content_data['value'] = parsed_value
                except json.JSONDecodeError:
                    content_data['value'] = {"featuredServices": []} # Fallback if JSON is invalid
            else:
                content_data['value'] = {"featuredServices": []} # Default if value is empty
            return content_data
        return {"value": {"featuredServices": []}} # Default if no content found
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/content/{key}")
async def update_content(key: str, content: Content, user: dict = Depends(get_current_user)):
    try:
        # Convert content value to JSON string before saving
        content_dict = content.dict()
        if 'value' in content_dict and content_dict['value'] is not None:
            content_dict['value'] = json.dumps(content_dict['value'])

        response, count = supabase.table('contents').update(content_dict).eq("key", key).execute()
        if not response[1]:
             # If key doesn't exist, create it
            response, count = supabase.table('contents').insert(content_dict).execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Services Management ---

@app.get("/services", response_model=List[Service])
async def get_all_services():
    try:
        response, count = supabase.table('services').select("*").execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/services")
async def create_service(service: Service, user: dict = Depends(get_current_user)):
    try:
        response, count = supabase.table('services').insert(service.dict()).execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/services/{service_id}")
async def update_service(service_id: str, service: Service, user: dict = Depends(get_current_user)):
    try:
        response, count = supabase.table('services').update(service.dict()).eq("id", service_id).execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/services/{service_id}")
async def delete_service(service_id: str, user: dict = Depends(get_current_user)):
    try:
        response, count = supabase.table('services').delete().eq("id", service_id).execute()
        return {"message": "Service deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Team Management ---

@app.get("/team-members", response_model=List[TeamMember])
async def get_team_members():
    try:
        response, count = supabase.table('team_members').select("*").execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/team-members")
async def create_team_member(member: TeamMember, user: dict = Depends(get_current_user)):
    try:
        response, count = supabase.table('team_members').insert(member.dict()).execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/team-members/{member_id}")
async def update_team_member(member_id: int, member: TeamMember, user: dict = Depends(get_current_user)):
    try:
        response, count = supabase.table('team_members').update(member.dict()).eq("id", member_id).execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/team-members/{member_id}")
async def delete_team_member(member_id: int, user: dict = Depends(get_current_user)):
    try:
        response, count = supabase.table('team_members').delete().eq("id", member_id).execute()
        return {"message": "Team member deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Portfolio Category Management ---

@app.get("/portfolio-categories", response_model=List[PortfolioCategory])
async def get_portfolio_categories():
    try:
        response, count = supabase.table('portfolio_categories').select("*").execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/portfolio-categories")
async def create_portfolio_category(category: PortfolioCategory, user: dict = Depends(get_current_user)):
    try:
        response, count = supabase.table('portfolio_categories').insert(category.dict()).execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/portfolio-categories/{category_id}")
async def delete_portfolio_category(category_id: int, user: dict = Depends(get_current_user)):
    try:
        # Optional: Check if any project is using this category before deleting
        response, count = supabase.table('portfolio_categories').delete().eq("id", category_id).execute()
        return {"message": "Category deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Portfolio Project Management ---

@app.get("/portfolio-projects", response_model=List[PortfolioProject])
async def get_portfolio_projects(category_id: Optional[int] = None):
    try:
        query = supabase.table('portfolio_projects').select("*")
        if category_id:
            query = query.eq('category_id', category_id)
        response, count = query.execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/portfolio-projects")
async def create_portfolio_project(project: PortfolioProject, user: dict = Depends(get_current_user)):
    try:
        response, count = supabase.table('portfolio_projects').insert(project.dict()).execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/portfolio-projects/{project_id}")
async def update_portfolio_project(project_id: int, project: PortfolioProject, user: dict = Depends(get_current_user)):
    try:
        response, count = supabase.table('portfolio_projects').update(project.dict()).eq("id", project_id).execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/portfolio-projects/{project_id}")
async def delete_portfolio_project(project_id: int, user: dict = Depends(get_current_user)):
    try:
        response, count = supabase.table('portfolio_projects').delete().eq("id", project_id).execute()
        return {"message": "Project deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Message Management ---

@app.get("/messages", response_model=List[Message])
async def get_all_messages(user: dict = Depends(get_current_user)):
    try:
        response, count = supabase.table('messages').select("*").order("received_at", desc=True).execute()
        return response[1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/messages")
async def create_message(message: Message):
    try:
        response, count = supabase.table('messages').insert(message.dict()).execute()
        return {"message": "Message sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/messages/{message_id}/read")
async def mark_message_as_read(message_id: str, user: dict = Depends(get_current_user)):
    try:
        response, count = supabase.table('messages').update({"is_read": True}).eq("id", message_id).execute()
        return {"message": "Message marked as read"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Image Upload ---
@app.post("/images/upload")
async def upload_image(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    try:
        file_content = await file.read()
        # Use a generic bucket name, or make it dynamic if needed
        bucket_name = "images" 
        file_path = f"public/{file.filename}"

        # Upload to Supabase Storage
        supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": file.content_type}
        )

        # Get public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)

        return {"message": "Image uploaded successfully", "url": public_url}
    except Exception as e:
        # More specific error handling can be added here
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")
