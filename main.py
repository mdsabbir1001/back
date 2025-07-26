print("Backend script started!")
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Form, Request
from fastapi.concurrency import run_in_threadpool
import traceback
from pydantic import BaseModel
from supabase import create_client, Client
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import uuid
import logging

# --- Basic Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

app = FastAPI()

# --- Global Exception Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception for request {request.method} {request.url}: {exc}", exc_info=True)
    return HTTPException(status_code=500, detail="Internal Server Error")

# --- CORS Configuration ---
# IMPORTANT: Replace "*" with your actual frontend URL for production.
# e.g., ["http://localhost:3000", "https://your-production-domain.com"]
origins = [
    "http://localhost:5174", # For local development
    "https://minimindcreatives.netlify.app",
    "https://minimind-backend.onrender.com",
    # "https://your-production-frontend.com" # Add your production frontend URL here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Supabase Client Initialization ---
try:
    url: str = os.environ["SUPABASE_URL"]
    key: str = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    supabase: Client = create_client(url, key)
except KeyError as e:
    logging.critical(f"Missing environment variable: {e}. Application cannot start.")
    # In a real app, you might want to exit or handle this more gracefully
    raise RuntimeError(f"Configuration error: Missing environment variable {e}")


# --- Email Configuration ---
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_EMAIL_PASSWORD = os.environ.get("SENDER_EMAIL_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")
MESSAGE_SENDER_EMAIL = os.environ.get("MESSAGE_SENDER_EMAIL")
MESSAGE_SENDER_EMAIL_PASSWORD = os.environ.get("MESSAGE_SENDER_EMAIL_PASSWORD")

# --- Security ---
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        user_response = await run_in_threadpool(supabase.auth.get_user, token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_response.user.dict()
    except Exception as e:
        logging.error(f"Authentication error: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

# --- Pydantic Models (assuming they are defined as before) ---
class UserCredentials(BaseModel):
    email: str
    password: str

class Content(BaseModel):
    key: str
    value: str

class MessageIn(BaseModel):
    name: str
    email: str
    subject: Optional[str] = None
    message: str
    read: Optional[bool] = False
    received_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)

class Message(BaseModel):
    name: str
    email: str
    subject: Optional[str] = None
    message: str
    read: Optional[bool] = False
    received_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)

class MessageOut(Message):
    id: str

class SendReplyEmailRequest(BaseModel):
    name: str
    email: str
    subject: Optional[str] = None
    originalMessage: str
    replyBody: str

class ReplyMessage(BaseModel):
    recipient_email: str
    subject: str
    body: str

class TeamMember(BaseModel):
    name: str
    designation: str
    image_url: str
    bio: Optional[str] = None
    specialties: Optional[List[str]] = None
    social_url_a: Optional[str] = None
    social_url_b: Optional[str] = None
    social_url_c: Optional[str] = None
    display_order: Optional[int] = None

class TeamMemberOut(TeamMember):
    id: int
    display_order: Optional[int]

class PortfolioCategory(BaseModel):
    id: int
    name: str

class PortfolioCategoryIn(BaseModel):
    name: str

class PortfolioProject(BaseModel):
    id: int
    title: str
    description: str
    image_url: str
    project_images: Optional[List[str]] = None
    category_name: str
    aspect_ratio: Optional[str] = None
    url: Optional[str] = None
    github_url: Optional[str] = None
    technologies: Optional[List[str]] = None

class PortfolioProjectIn(BaseModel):
    title: str
    description: str
    image_url: str
    project_images: Optional[List[str]] = None
    category_name: str
    aspect_ratio: Optional[str] = None
    url: Optional[str] = None
    github_url: Optional[str] = None
    technologies: Optional[List[str]] = None

class Service(BaseModel):
    title: str
    description: str
    icon: str
    price: Optional[str] = None
    features: List[str]
    cover_image_url: Optional[str] = None

class ServiceOut(Service):
    id: str

class ContactInfo(BaseModel):
    id: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    business_hours: Optional[str] = None
    social_links: Optional[dict] = None

class HomePageContent(BaseModel):
    hero_title: Optional[str] = None
    hero_subtitle: Optional[str] = None
    hero_description: Optional[str] = None
    cta_title: Optional[str] = None
    cta_subtitle: Optional[str] = None

class HeroImageIn(BaseModel):
    image_url: Optional[str] = None
    display_order: int

class HeroImageOut(HeroImageIn):
    id: int

class HomeStatIn(BaseModel):
    number: str
    label: str
    icon_name: Optional[str] = None
    display_order: int

class HomeStatOut(HomeStatIn):
    id: Optional[str] = None

class HomeServicePreviewIn(BaseModel):
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    display_order: int

class HomeServicePreviewOut(HomeServicePreviewIn):
    id: int

class FullHomePage(BaseModel):
    content: HomePageContent
    hero_images: List[HeroImageOut]
    stats: List[HomeStatOut]
    services_preview: List[HomeServicePreviewOut]

class Order(BaseModel):
    order_id: str
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    message: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    package_name: str
    package_price: str
    status: str = 'pending'
    created_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)

class Package(BaseModel):
    name: str
    description: str
    price: str
    features: List[str]
    is_popular: Optional[bool] = False

class PackageOut(Package):
    id: str

class Review(BaseModel):
    name: str
    designation: str
    company: Optional[str] = None
    company_url: Optional[str] = None
    project: Optional[str] = None
    rating: int
    review: str
    image_url: Optional[str] = None
    approved: Optional[bool] = False

class ReviewOut(Review):
    id: str
    company_url: str
    created_at: datetime.datetime

class ReviewsStat(BaseModel):
    id: Optional[str] = None
    order: int
    number: str
    label: str

# --- Root ---
@app.get("/")
def read_root():
    return {"Hello": "Minimind API"}

# --- Auth Endpoints ---
@app.post("/signup")
async def signup(credentials: UserCredentials):
    try:
        auth_response = await run_in_threadpool(supabase.auth.sign_up, {
            "email": credentials.email,
            "password": credentials.password,
        })
        user_id = auth_response.user.id
        await run_in_threadpool(supabase.table('users').insert({"id": user_id, "email": credentials.email}).execute)
        return {"message": "User created successfully", "user_id": user_id}
    except Exception as e:
        logging.error(f"Signup failed for email {credentials.email}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/login")
async def login(credentials: UserCredentials):
    try:
        auth_response = await run_in_threadpool(supabase.auth.sign_in_with_password, {
            "email": credentials.email,
            "password": credentials.password,
        })
        return {"message": "Login successful", "user": auth_response.user.email, "access_token": auth_response.session.access_token, "refresh_token": auth_response.session.refresh_token}
    except Exception as e:
        logging.error(f"Login failed for email {credentials.email}: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail=str(e))

# --- Content Management ---
@app.get("/content/{key}")
async def get_content(key: str):
    try:
        response = await run_in_threadpool(supabase.table('contents').select("*").eq("key", key).single().execute)
        if response.data:
            content_data = response.data
            if 'value' in content_data and content_data['value']:
                try:
                    parsed_value = json.loads(content_data['value'])
                    if 'featuredServices' not in parsed_value or not isinstance(parsed_value['featuredServices'], list):
                        parsed_value['featuredServices'] = []
                    content_data['value'] = parsed_value
                except json.JSONDecodeError:
                    content_data['value'] = {"featuredServices": []}
            else:
                content_data['value'] = {"featuredServices": []}
            return content_data
        return {"value": {"featuredServices": []}}
    except Exception as e:
        logging.error(f"Failed to get content for key '{key}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve content: {str(e)}")

@app.put("/content/{key}")
async def update_content(key: str, content: Content, user: dict = Depends(get_current_user)):
    try:
        content_dict = content.dict()
        if 'value' in content_dict and content_dict['value'] is not None:
            content_dict['value'] = json.dumps(content_dict['value'])

        response = await run_in_threadpool(supabase.table('contents').update(content_dict).eq("key", key).execute)
        if not response.data:
            response = await run_in_threadpool(supabase.table('contents').insert(content_dict).execute)
        return response.data
    except Exception as e:
        logging.error(f"Failed to update content for key '{key}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Contact Info Management ---
@app.get("/contact-info", response_model=ContactInfo)
async def get_contact_info():
    try:
        response = await run_in_threadpool(supabase.table('contact_info').select("*").limit(1).execute)
        if response.data:
            contact_data = response.data[0]
            if 'socialLinks' in contact_data:
                if isinstance(contact_data['socialLinks'], str):
                    try:
                        contact_data['socialLinks'] = json.loads(contact_data['socialLinks'])
                    except json.JSONDecodeError:
                        contact_data['socialLinks'] = {}
                elif contact_data['socialLinks'] is None:
                    contact_data['socialLinks'] = {}
            return contact_data
        return ContactInfo()
    except Exception as e:
        logging.error(f"Failed to get contact info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/contact-info")
async def update_contact_info(info: ContactInfo, user: dict = Depends(get_current_user)):
    try:
        info_dict = info.dict(exclude_unset=True)
        if 'socialLinks' in info_dict and isinstance(info_dict['socialLinks'], dict):
            info_dict['socialLinks'] = json.dumps(info_dict['socialLinks'])

        response = await run_in_threadpool(supabase.table('contact_info').update(info_dict).eq("id", 1).execute)
        if not response.data:
            response = await run_in_threadpool(supabase.table('contact_info').insert({"id": 1, **info_dict}).execute)
        return response.data
    except Exception as e:
        logging.error(f"Failed to update contact info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Reviews Stats Management ---
@app.get("/reviews-stats", response_model=List[ReviewsStat])
async def get_reviews_stats():
    try:
        response = await run_in_threadpool(supabase.table('reviews_stats').select("*").order("order").execute)
        return response.data
    except Exception as e:
        logging.error(f"Failed to get reviews stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reviews-stats", response_model=ReviewsStat)
async def create_reviews_stat(stat: ReviewsStat, user: dict = Depends(get_current_user)):
    try:
        stat_data = stat.dict()
        if stat_data.get("id") is None:
            del stat_data["id"]
        response = await run_in_threadpool(supabase.table('reviews_stats').insert(stat_data).execute)
        return response.data[0]
    except Exception as e:
        logging.error(f"Failed to create reviews stat: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/reviews-stats/{stat_id}", response_model=ReviewsStat)
async def update_reviews_stat(stat_id: str, stat: ReviewsStat, user: dict = Depends(get_current_user)):
    try:
        response = await run_in_threadpool(supabase.table('reviews_stats').update(stat.dict(exclude_unset=True)).eq("id", stat_id).execute)
        return response.data[0]
    except Exception as e:
        logging.error(f"Failed to update reviews stat {stat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/reviews-stats/{stat_id}")
async def delete_reviews_stat(stat_id: str, user: dict = Depends(get_current_user)):
    try:
        await run_in_threadpool(supabase.table('reviews_stats').delete().eq("id", stat_id).execute)
        return {"message": "Reviews stat deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete reviews stat {stat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Home Page Management ---
@app.get("/home-page", response_model=FullHomePage)
async def get_full_home_page():
    try:
        content_res, images_res, stats_res, services_res = await asyncio.gather(
            run_in_threadpool(supabase.table('home_content').select("*").limit(1).execute),
            run_in_threadpool(supabase.table('hero_images').select("*").order("display_order").execute),
            run_in_threadpool(supabase.table('home_stats').select("*").order("display_order").execute),
            run_in_threadpool(supabase.table('home_services_preview').select("*").order("display_order").execute)
        )

        return {
            "content": content_res.data[0] if content_res.data else {},
            "hero_images": images_res.data if images_res.data else [],
            "stats": [ {**stat, "id": str(stat["id"])} for stat in stats_res.data ] if stats_res.data else [],
            "services_preview": services_res.data if services_res.data else []
        }
    except Exception as e:
        logging.error(f"Failed to get home page data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.put("/home-page")
async def update_full_home_page(data: FullHomePage, user: dict = Depends(get_current_user)):
    try:
        # Using a transaction might be better here, but for simplicity, we'll do sequential calls.
        await run_in_threadpool(supabase.table('home_content').upsert(data.content.dict()).execute)

        await run_in_threadpool(supabase.table('hero_images').delete().neq('id', -1).execute) # Delete all
        if data.hero_images:
            await run_in_threadpool(supabase.table('hero_images').insert([img.dict() for img in data.hero_images]).execute)

        await run_in_threadpool(supabase.table('home_stats').delete().neq('id', -1).execute)
        if data.stats:
            await run_in_threadpool(supabase.table('home_stats').insert([stat.dict() for stat in data.stats]).execute)

        await run_in_threadpool(supabase.table('home_services_preview').delete().neq('id', -1).execute)
        if data.services_preview:
            await run_in_threadpool(supabase.table('home_services_preview').insert([service.dict() for service in data.services_preview]).execute)

        return {"message": "Home page updated successfully"}
    except Exception as e:
        logging.error(f"Failed to update home page: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Service Management ---
@app.get("/services", response_model=List[ServiceOut])
async def get_all_services():
    try:
        response = await run_in_threadpool(supabase.table('services').select("*").order("id").execute)
        return response.data
    except Exception as e:
        logging.error(f"Failed to get services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/services", response_model=ServiceOut)
async def create_service(service: Service, user: dict = Depends(get_current_user)):
    try:
        service_data = service.dict()
        if 'coverImage' in service_data:
            service_data['cover_image_url'] = service_data.pop('coverImage')
        response = await run_in_threadpool(supabase.table('services').insert(service_data).execute)
        return response.data[0]
    except Exception as e:
        logging.error(f"Failed to create service: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/services/{service_id}", response_model=ServiceOut)
async def update_service(service_id: str, service: Service, user: dict = Depends(get_current_user)):
    try:
        service_data = service.dict(exclude_unset=True)
        if 'coverImage' in service_data:
            service_data['cover_image_url'] = service_data.pop('coverImage')
        response = await run_in_threadpool(supabase.table('services').update(service_data).eq("id", service_id).execute)
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Service with id {service_id} not found.")
        return response.data[0]
    except Exception as e:
        logging.error(f"Failed to update service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/services/{service_id}")
async def delete_service(service_id: str, user: dict = Depends(get_current_user)):
    try:
        response = await run_in_threadpool(supabase.table('services').delete().eq("id", service_id).execute)
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Service with id {service_id} not found.")
        return {"message": "Service deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Team Management ---
@app.get("/team-members", response_model=List[TeamMemberOut])
async def get_team_members():
    try:
        response = await run_in_threadpool(supabase.table('team_members').select("*").order('display_order').execute)
        team_members = response.data
        team_members.sort(key=lambda x: x.get('display_order') if x.get('display_order') is not None else float('inf'))
        for member in team_members:
            if isinstance(member.get('specialties'), str):
                try:
                    member['specialties'] = json.loads(member['specialties'])
                except json.JSONDecodeError:
                    member['specialties'] = []
        return team_members
    except Exception as e:
        logging.error(f"Failed to get team members: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/team-members")
async def create_team_member(member: TeamMember, user: dict = Depends(get_current_user)):
    try:
        count_res = await run_in_threadpool(supabase.table('team_members').select("display_order", count='exact').order('display_order', desc=True).limit(1).execute)
        max_order = 0
        if count_res.data:
            max_order = count_res.data[0]['display_order']
        
        member_data = member.dict()
        member_data['display_order'] = max_order + 1

        if 'specialties' in member_data and isinstance(member_data['specialties'], list):
            member_data['specialties'] = json.dumps(member_data['specialties'])
        
        response = await run_in_threadpool(supabase.table('team_members').insert(member_data).execute)
        return response.data
    except Exception as e:
        logging.error(f"Failed to create team member: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/team-members/{member_id}")
async def update_team_member(member_id: str, member: TeamMember, user: dict = Depends(get_current_user)):
    try:
        member_data = member.dict(exclude_unset=True)
        if 'specialties' in member_data and isinstance(member_data['specialties'], list):
            member_data['specialties'] = json.dumps(member_data['specialties'])

        response = await run_in_threadpool(supabase.table('team_members').update(member_data).eq("id", member_id).execute)
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Team member with id {member_id} not found.")
        return response.data
    except Exception as e:
        logging.error(f"Failed to update team member {member_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/team-members/{member_id}")
async def delete_team_member(member_id: str, user: dict = Depends(get_current_user)):
    try:
        response = await run_in_threadpool(supabase.table('team_members').delete().eq("id", member_id).execute)
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Team member with id {member_id} not found.")
        return {"message": "Team member deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete team member {member_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

class TeamOrder(BaseModel):
    ordered_ids: List[int]

@app.post("/team-members/reorder")
async def reorder_team_members(order: TeamOrder, user: dict = Depends(get_current_user)):
    try:
        # This could be done in a transaction for atomicity
        for index, member_id in enumerate(order.ordered_ids):
            await run_in_threadpool(supabase.table('team_members').update({'display_order': index}).eq('id', member_id).execute)
        return {"message": "Team members reordered successfully"}
    except Exception as e:
        logging.error(f"Failed to reorder team members: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Portfolio Category Management ---
@app.get("/portfolio-categories", response_model=List[PortfolioCategory])
async def get_portfolio_categories():
    try:
        response = await run_in_threadpool(supabase.table('portfolio_categories').select("*").execute)
        return response.data
    except Exception as e:
        logging.error(f"Failed to get portfolio categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/portfolio-categories", response_model=PortfolioCategory)
async def create_portfolio_category(category: PortfolioCategoryIn, user: dict = Depends(get_current_user)):
    try:
        response = await run_in_threadpool(supabase.table('portfolio_categories').insert(category.dict()).execute)
        return response.data[0]
    except Exception as e:
        logging.error(f"Failed to create portfolio category: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/portfolio-categories/{category_id}")
async def delete_portfolio_category(category_id: str, user: dict = Depends(get_current_user)):
    try:
        await run_in_threadpool(supabase.table('portfolio_categories').delete().eq("id", category_id).execute)
        return {"message": "Category deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete portfolio category {category_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Portfolio Project Management ---
@app.get("/portfolio-projects", response_model=List[PortfolioProject])
async def get_portfolio_projects(category_name: Optional[str] = None):
    try:
        query = supabase.table('portfolio_projects').select("*, portfolio_categories(name)").order('updated_at', desc=True)
        if category_name:
            query = query.eq('portfolio_categories.name', category_name)
        response = await run_in_threadpool(query.execute)

        projects = []
        for item in response.data:
            project = {
                "id": item["id"],
                "title": item["title"],
                "description": item["description"],
                "image_url": item["image_url"],
                "project_images": item.get("project_images"),
                "category_name": item["portfolio_categories"]["name"],
                "aspect_ratio": item.get("aspect_ratio"),
                "url": item.get("url"),
                "github_url": item.get("github_url"),
                "technologies": item.get("technologies")
            }
            projects.append(project)
        return projects
    except Exception as e:
        logging.error(f"Failed to get portfolio projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/portfolio-projects", response_model=PortfolioProject)
async def create_portfolio_project(project: PortfolioProjectIn, user: dict = Depends(get_current_user)):
    try:
        category_response = await run_in_threadpool(supabase.table('portfolio_categories').select("id").eq("name", project.category_name).single().execute)
        category_id = None
        if category_response.data:
            category_id = category_response.data["id"]
        else:
            new_category_response = await run_in_threadpool(supabase.table('portfolio_categories').insert({"name": project.category_name}).execute)
            category_id = new_category_response.data[0]["id"]

        project_data = project.dict()
        project_data["category_id"] = category_id
        del project_data["category_name"]

        response = await run_in_threadpool(supabase.table('portfolio_projects').insert(project_data).execute)
        
        new_project = response.data[0]
        new_project["category_name"] = project.category_name
        
        return new_project
    except Exception as e:
        logging.error(f"Failed to create portfolio project: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/portfolio-projects/{project_id}")
async def update_portfolio_project(project_id: str, project: PortfolioProjectIn, user: dict = Depends(get_current_user)):
    try:
        category_response = await run_in_threadpool(supabase.table('portfolio_categories').select("id").eq("name", project.category_name).single().execute)
        category_id = None
        if category_response.data:
            category_id = category_response.data["id"]
        else:
            new_category_response = await run_in_threadpool(supabase.table('portfolio_categories').insert({"name": project.category_name}).execute)
            category_id = new_category_response.data[0]["id"]

        project_data = project.dict(exclude_unset=True)
        project_data["category_id"] = category_id
        del project_data["category_name"]

        response = await run_in_threadpool(supabase.table('portfolio_projects').update(project_data).eq("id", project_id).execute)
        return response.data
    except Exception as e:
        logging.error(f"Failed to update portfolio project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/portfolio-projects/{project_id}")
async def delete_portfolio_project(project_id: str, user: dict = Depends(get_current_user)):
    try:
        await run_in_threadpool(supabase.table('portfolio_projects').delete().eq("id", project_id).execute)
        return {"message": "Project deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete portfolio project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Order Management ---
def _send_email_notification(order_details: dict):
    if not all([SENDER_EMAIL, SENDER_EMAIL_PASSWORD, RECEIVER_EMAIL]):
        logging.warning("Email notification for new order is not configured. Skipping.")
        return

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"New Package Order: {order_details.get('package_name', 'N/A')}"

    body = f'''
    A new package order has been placed!

    Order ID: {order_details.get('order_id', 'N/A')}
    Package Name: {order_details.get('package_name', 'N/A')}
    Package Price: {order_details.get('package_price', 'N/A')}

    Customer Details:
    Name: {order_details.get('name', 'N/A')}
    Email: {order_details.get('email', 'N/A')}
    Phone: {order_details.get('phone', 'N/A')}
    Company: {order_details.get('company', 'N/A')}

    Project Details:
    Budget: {order_details.get('budget', 'N/A')}
    Timeline: {order_details.get('timeline', 'N/A')}
    Message: {order_details.get('message', 'N/A')}

    Please check the admin dashboard for more details.
    '''
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_EMAIL_PASSWORD)
            smtp.send_message(msg)
            logging.info(f"New order notification sent for order {order_details.get('order_id')}")
    except Exception as e:
        logging.error(f"Failed to send new order email notification: {e}", exc_info=True)

@app.post("/orders")
async def create_order(order: Order):
    try:
        order_data = order.dict()
        order_data['created_at'] = order_data['created_at'].isoformat()
        response = await run_in_threadpool(supabase.table('orders').insert(order_data).execute)
        if response.data:
            await run_in_threadpool(_send_email_notification, response.data[0])
        return response.data
    except Exception as e:
        logging.error(f"Failed to create order: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/orders", response_model=List[Order])
async def get_all_orders(user: dict = Depends(get_current_user)):
    try:
        response = await run_in_threadpool(supabase.table('orders').select("*, created_at").order("created_at", desc=True).execute)
        return response.data
    except Exception as e:
        logging.error(f"Failed to get all orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, user: dict = Depends(get_current_user)):
    try:
        response = await run_in_threadpool(supabase.table('orders').select("*").eq("order_id", order_id).single().execute)
        return response.data
    except Exception as e:
        logging.error(f"Failed to get order {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/orders/{order_id}")
async def update_order_status(order_id: str, status: str, user: dict = Depends(get_current_user)):
    try:
        response = await run_in_threadpool(supabase.table('orders').update({"status": status}).eq("order_id", order_id).execute)
        return response.data
    except Exception as e:
        logging.error(f"Failed to update order {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/orders/{order_id}")
async def delete_order(order_id: str, user: dict = Depends(get_current_user)):
    try:
        await run_in_threadpool(supabase.table('orders').delete().eq("order_id", order_id).execute)
        return {"message": "Order deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete order {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Package Management ---
@app.get("/packages", response_model=List[PackageOut])
async def get_all_packages():
    try:
        response = await run_in_threadpool(supabase.table('packages').select("*").order("id").execute)
        packages = []
        for item in response.data:
            package = {
                "id": item["id"],
                "name": item["title"],
                "description": item["description"],
                "price": item["price"],
                "features": item["features"],
                "is_popular": item["is_popular"]
            }
            packages.append(package)
        return packages
    except Exception as e:
        logging.error(f"Failed to get packages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/packages")
async def create_package(package: Package, user: dict = Depends(get_current_user)):
    try:
        package_data = package.dict()
        package_data["title"] = package_data.pop("name")
        response = await run_in_threadpool(supabase.table('packages').insert(package_data).execute)
        if response.data:
            return response.data
        else:
            error_message = response.error.message if response.error else "Failed to create package in Supabase"
            logging.error(f"Failed to create package: {error_message}")
            raise HTTPException(status_code=400, detail=error_message)
    except Exception as e:
        logging.error(f"Failed to create package: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/packages/{package_id}")
async def update_package(package_id: str, package: Package, user: dict = Depends(get_current_user)):
    try:
        package_data = package.dict(exclude_unset=True)
        if "name" in package_data:
            package_data["title"] = package_data.pop("name")
        response = await run_in_threadpool(supabase.table('packages').update(package_data).eq("id", package_id).execute)
        if response.data:
            return response.data
        else:
            error_message = response.error.message if response.error else "Failed to update package in Supabase"
            logging.error(f"Failed to update package {package_id}: {error_message}")
            raise HTTPException(status_code=400, detail=error_message)
    except Exception as e:
        logging.error(f"Failed to update package {package_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/packages/{package_id}")
async def delete_package(package_id: str, user: dict = Depends(get_current_user)):
    try:
        await run_in_threadpool(supabase.table('packages').delete().eq("id", package_id).execute)
        return {"message": "Package deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete package {package_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Review Management ---
@app.post("/reviews", response_model=ReviewOut)
async def create_review(review: Review):
    try:
        review_data = review.dict()
        response = await run_in_threadpool(supabase.table('reviews').insert(review_data).execute)
        return response.data[0]
    except Exception as e:
        logging.error(f"Failed to create review: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/admin/reviews", response_model=List[ReviewOut])
async def get_all_reviews(user: dict = Depends(get_current_user)):
    try:
        response = await run_in_threadpool(supabase.table('reviews').select("*").order("created_at", desc=True).execute)
        return response.data
    except Exception as e:
        logging.error(f"Failed to get all reviews: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reviews", response_model=List[ReviewOut])
async def get_public_reviews():
    try:
        response = await run_in_threadpool(supabase.table('reviews').select("*").eq('approved', True).order("created_at", desc=True).execute)
        return response.data
    except Exception as e:
        logging.error(f"Failed to get public reviews: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/reviews/{review_id}", response_model=ReviewOut)
async def update_review(review_id: str, review: Review, user: dict = Depends(get_current_user)):
    try:
        review_data = review.dict(exclude_unset=True)
        response = await run_in_threadpool(supabase.table('reviews').update(review_data).eq('id', review_id).execute)
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Review with id {review_id} not found.")
        return response.data[0]
    except Exception as e:
        logging.error(f"Failed to update review {review_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/reviews/{review_id}/approve", response_model=ReviewOut)
async def approve_review(review_id: str, user: dict = Depends(get_current_user)):
    try:
        response = await run_in_threadpool(supabase.table('reviews').update({"approved": True}).eq("id", review_id).execute)
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Review with id {review_id} not found.")
        return response.data[0]
    except Exception as e:
        logging.error(f"Failed to approve review {review_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/reviews/{review_id}")
async def delete_review(review_id: str, user: dict = Depends(get_current_user)):
    try:
        response = await run_in_threadpool(supabase.table('reviews').delete().eq("id", review_id).execute)
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Review with id {review_id} not found.")
        return {"message": "Review deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete review {review_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Message Management ---
@app.get("/messages", response_model=List[MessageOut])
async def get_all_messages(user: dict = Depends(get_current_user)):
    try:
        response = await run_in_threadpool(supabase.table('messages').select("id, name, email, subject, message, read, received_at").order("received_at", desc=True).execute)
        return response.data
    except Exception as e:
        logging.error(f"Failed to get messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def _send_new_message_email(message_details: dict):
    if not all([MESSAGE_SENDER_EMAIL, MESSAGE_SENDER_EMAIL_PASSWORD, RECEIVER_EMAIL]):
        logging.warning("Email for new message is not configured. Skipping.")
        return

    msg = MIMEMultipart()
    msg['From'] = MESSAGE_SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"New Contact Message: {message_details.get('subject', 'No Subject')}"

    body = f'''
    You have received a new contact message!

    Name: {message_details.get('name', 'N/A')}
    Email: {message_details.get('email', 'N/A')}
    Subject: {message_details.get('subject', 'N/A')}
    Message:
    {message_details.get('message', 'N/A')}

    Received At: {message_details.get('received_at', 'N/A')}

    Please check the admin dashboard for more details and to reply.
    '''
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(MESSAGE_SENDER_EMAIL, MESSAGE_SENDER_EMAIL_PASSWORD)
            smtp.send_message(msg)
            logging.info(f"New message notification sent for message from {message_details.get('email')}")
    except Exception as e:
        logging.error(f"Failed to send new message email notification: {e}", exc_info=True)

@app.post("/messages")
async def create_message(message: MessageIn):
    try:
        message_data = message.dict()
        message_data['received_at'] = message_data['received_at'].isoformat()
        response = await run_in_threadpool(supabase.table('messages').insert(message_data).execute)
        if response.data:
            await run_in_threadpool(_send_new_message_email, message_data)
        return {"message": "Message sent successfully"}
    except Exception as e:
        logging.error(f"Failed to create message: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/messages/{message_id}/read")
async def mark_message_as_read(message_id: str, user: dict = Depends(get_current_user)):
    try:
        await run_in_threadpool(supabase.table('messages').update({"read": True}).eq("id", message_id).execute)
        return {"message": "Message marked as read"}
    except Exception as e:
        logging.error(f"Failed to mark message {message_id} as read: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/messages/{message_id}")
async def delete_message(message_id: str, user: dict = Depends(get_current_user)):
    try:
        await run_in_threadpool(supabase.table('messages').delete().eq("id", message_id).execute)
        return {"message": "Message deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete message {message_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def _send_reply(reply: ReplyMessage):
    if not all([MESSAGE_SENDER_EMAIL, MESSAGE_SENDER_EMAIL_PASSWORD]):
        logging.error("Email sending (reply) not configured.")
        raise HTTPException(status_code=500, detail="Email sending not configured.")

    msg = MIMEMultipart()
    msg['From'] = MESSAGE_SENDER_EMAIL
    msg['To'] = reply.recipient_email
    msg['Subject'] = reply.subject
    msg.attach(MIMEText(reply.body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(MESSAGE_SENDER_EMAIL, MESSAGE_SENDER_EMAIL_PASSWORD)
            smtp.send_message(msg)
            logging.info(f"Reply sent to {reply.recipient_email}")
    except Exception as e:
        logging.error(f"Failed to send reply to {reply.recipient_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send reply: {e}")

@app.post("/messages/reply")
async def reply_to_message(reply: ReplyMessage, user: dict = Depends(get_current_user)):
    await run_in_threadpool(_send_reply, reply)
    return {"message": "Reply sent successfully"}

def _send_reply_email_from_request(reply_data: SendReplyEmailRequest):
    if not all([MESSAGE_SENDER_EMAIL, MESSAGE_SENDER_EMAIL_PASSWORD]):
        logging.error("Email sending (reply) not configured.")
        raise HTTPException(status_code=500, detail="Email sending not configured in backend.")

    msg = MIMEMultipart()
    msg['From'] = MESSAGE_SENDER_EMAIL
    msg['To'] = reply_data.email
    msg['Subject'] = f"Re: {reply_data.subject or 'Your Message'}"

    body = f'''
    Dear {reply_data.name},

    {reply_data.replyBody}

    ---
    Original Message:
    From: {reply_data.name} <{reply_data.email}>
    Subject: {reply_data.subject or 'No Subject'}
    Message:
    {reply_data.originalMessage}
    '''
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(MESSAGE_SENDER_EMAIL, MESSAGE_SENDER_EMAIL_PASSWORD)
            smtp.send_message(msg)
            logging.info(f"Reply sent to {reply_data.email} via backend endpoint.")
    except Exception as e:
        logging.error(f"Failed to send reply via backend endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send reply via backend: {e}")

@app.post("/send-reply-email")
async def send_reply_email(reply_data: SendReplyEmailRequest):
    await run_in_threadpool(_send_reply_email_from_request, reply_data)
    return {"message": "Reply sent successfully via backend."}

# --- Image Upload ---
@app.post("/images/upload")
async def upload_image(file: Optional[UploadFile] = File(None), image_url: Optional[str] = Form(None)):
    if not file and not image_url:
        raise HTTPException(status_code=400, detail="No image file or URL provided.")

    if file:
        try:
            file_content = await file.read()
            bucket_name = "images"
            file_extension = file.filename.split(".")[-1]
            file_path = f"{uuid.uuid4()}.{file_extension}"

            await run_in_threadpool(
                supabase.storage.from_(bucket_name).upload,
                path=file_path,
                file=file_content,
                file_options={"content-type": file.content_type}
            )

            public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
            logging.info(f"Image uploaded to {public_url}")
            return {"message": "Image uploaded successfully", "url": public_url}
        except Exception as e:
            logging.error(f"Image upload failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")
    
    if image_url:
        # If only a URL is provided, we just acknowledge it.
        # You might want to add logic to fetch and store the image from the URL.
        logging.info(f"Image URL received: {image_url}")
        return {"message": "Image URL received", "url": image_url}
# --- Home Page Management ---