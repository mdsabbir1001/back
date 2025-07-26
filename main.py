print("Backend script started!")
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Form, Request
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

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled exception: {exc}")
    traceback.print_exc()
    return HTTPException(status_code=500, detail="Internal Server Error")

origins = [
    "http://localhost:5174",
    "*" # Temporarily allow all origins for testing CORS
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

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_EMAIL_PASSWORD = os.environ.get("SENDER_EMAIL_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")
MESSAGE_SENDER_EMAIL = os.environ.get("MESSAGE_SENDER_EMAIL")
MESSAGE_SENDER_EMAIL_PASSWORD = os.environ.get("MESSAGE_SENDER_EMAIL_PASSWORD")

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

# --- Home Page Models ---
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
        return {"message": "Login successful", "user": auth_response.user.email, "access_token": auth_response.session.access_token, "refresh_token": auth_response.session.refresh_token}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

# --- Content Management ---

@app.get("/content/{key}")
async def get_content(key: str):
    try:
        response = supabase.table('contents').select("*").eq("key", key).single().execute()
        if response.data:
            content_data = response.data
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

        response = supabase.table('contents').update(content_dict).eq("key", key).execute()
        if not response.data:
             # If key doesn't exist, create it
            response = supabase.table('contents').insert(content_dict).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@app.get("/contact-info", response_model=ContactInfo)
async def get_contact_info():
    try:
        response = supabase.table('contact_info').select("*").limit(1).execute()
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
        
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/contact-info")
async def update_contact_info(info: ContactInfo, user: dict = Depends(get_current_user)):
    try:
        info_dict = info.dict(exclude_unset=True)
        if 'socialLinks' in info_dict and isinstance(info_dict['socialLinks'], dict):
            info_dict['socialLinks'] = json.dumps(info_dict['socialLinks'])

        response = supabase.table('contact_info').update(info_dict).eq("id", 1).execute() # Assuming a single row with ID 1

        if not response.data:
            # If no row was updated, try to insert (for the first time)
            response = supabase.table('contact_info').insert({"id": 1, **info_dict}).execute()

        return response.data
    except Exception as e:
        
        raise HTTPException(status_code=500, detail=str(e))






# --- Reviews Stats Management ---

@app.get("/reviews-stats", response_model=List[ReviewsStat])
async def get_reviews_stats():
    try:
        response = supabase.table('reviews_stats').select("*").order("order").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reviews-stats", response_model=ReviewsStat)
async def create_reviews_stat(stat: ReviewsStat, user: dict = Depends(get_current_user)):
    try:
        stat_data = stat.dict()
        if stat_data.get("id") is None:
            del stat_data["id"]
        response = supabase.table('reviews_stats').insert(stat_data).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/reviews-stats/{stat_id}", response_model=ReviewsStat)
async def update_reviews_stat(stat_id: str, stat: ReviewsStat, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('reviews_stats').update(stat.dict(exclude_unset=True)).eq("id", stat_id).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/reviews-stats/{stat_id}")
async def delete_reviews_stat(stat_id: str, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('reviews_stats').delete().eq("id", stat_id).execute()
        return {"message": "Reviews stat deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# --- Home Page Management ---

@app.get("/home-page", response_model=FullHomePage)
async def get_full_home_page():
    try:
        content_res = supabase.table('home_content').select("*").limit(1).execute()
        images_res = supabase.table('hero_images').select("*").order("display_order").execute()
        stats_res = supabase.table('home_stats').select("*").order("display_order").execute()
        services_res = supabase.table('home_services_preview').select("*").order("display_order").execute()

        return {
            "content": content_res.data[0] if content_res.data else {},
            "hero_images": images_res.data if images_res.data else [],
            "stats": [ {**stat, "id": str(stat["id"])} for stat in stats_res.data ] if stats_res.data else [],
            "services_preview": services_res.data if services_res.data else []
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.put("/home-page")
async def update_full_home_page(data: FullHomePage, user: dict = Depends(get_current_user)):
    try:
        # Update home_content (assuming one row with id=1, or upsert)
        supabase.table('home_content').upsert(data.content.dict()).execute()

        # Clear and insert hero_images, stats, and services_preview to ensure consistency
        supabase.table('hero_images').delete().execute() # Delete all
        if data.hero_images:
            supabase.table('hero_images').insert([img.dict() for img in data.hero_images]).execute()

        supabase.table('home_stats').delete().execute()
        if data.stats:
            supabase.table('home_stats').insert([stat.dict() for stat in data.stats]).execute()

        supabase.table('home_services_preview').delete().execute()
        if data.services_preview:
            supabase.table('home_services_preview').insert([service.dict() for service in data.services_preview]).execute()

        return {"message": "Home page updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Image Upload ---

@app.get("/services", response_model=List[ServiceOut])
async def get_all_services():
    try:
        response = supabase.table('services').select("*").order("id").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/services", response_model=ServiceOut)
async def create_service(service: Service, user: dict = Depends(get_current_user)):
    try:
        service_data = service.dict()
        # Map coverImage from Pydantic model to cover_image_url for Supabase
        if 'coverImage' in service_data:
            service_data['cover_image_url'] = service_data.pop('coverImage')
        response = supabase.table('services').insert(service_data).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/services/{service_id}", response_model=ServiceOut)
async def update_service(service_id: str, service: Service, user: dict = Depends(get_current_user)):
    try:
        service_data = service.dict(exclude_unset=True)
        # Map coverImage from Pydantic model to cover_image_url for Supabase
        if 'coverImage' in service_data:
            service_data['cover_image_url'] = service_data.pop('coverImage')
        response = supabase.table('services').update(service_data).eq("id", service_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Service with id {service_id} not found.")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/services/{service_id}")
async def delete_service(service_id: str, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('services').delete().eq("id", service_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Service with id {service_id} not found.")
        return {"message": "Service deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Team Management ---

@app.get("/team-members", response_model=List[TeamMemberOut])
async def get_team_members():
    try:
        response = supabase.table('team_members').select("*").order('display_order').execute()
        team_members = response.data
        # Sort team members by display_order, with None values at the end
        team_members.sort(key=lambda x: x.get('display_order') if x.get('display_order') is not None else float('inf'))
        for member in team_members:
            if isinstance(member.get('specialties'), str):
                try:
                    member['specialties'] = json.loads(member['specialties'])
                except json.JSONDecodeError:
                    member['specialties'] = []
        return team_members
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/team-members")
async def create_team_member(member: TeamMember, user: dict = Depends(get_current_user)):
    try:
        # Get the highest display_order and add 1
        count_res = supabase.table('team_members').select("display_order", count='exact').order('display_order', desc=True).limit(1).execute()
        max_order = 0
        if count_res.data:
            max_order = count_res.data[0]['display_order']
        
        member_data = member.dict()
        member_data['display_order'] = max_order + 1

        # Ensure specialties list is stored as a JSON string if the DB column is text/json/jsonb
        if 'specialties' in member_data and isinstance(member_data['specialties'], list):
            member_data['specialties'] = json.dumps(member_data['specialties'])
        
        response = supabase.table('team_members').insert(member_data).execute()
        return response.data
    except Exception as e:
        
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/team-members/{member_id}")
async def update_team_member(member_id: str, member: TeamMember, user: dict = Depends(get_current_user)):
    try:
        member_data = member.dict(exclude_unset=True)
        # Ensure specialties list is stored as a JSON string
        if 'specialties' in member_data and isinstance(member_data['specialties'], list):
            member_data['specialties'] = json.dumps(member_data['specialties'])

        response = supabase.table('team_members').update(member_data).eq("id", member_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Team member with id {member_id} not found.")

        return response.data
    except Exception as e:
        
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/team-members/{member_id}")
async def delete_team_member(member_id: str, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('team_members').delete().eq("id", member_id).execute()
        
        if not response.data:
            # This can happen if the ID is not found. Frontend will get a 404.
            raise HTTPException(status_code=404, detail=f"Team member with id {member_id} not found.")

        return {"message": "Team member deleted successfully"}
    except Exception as e:
        
        raise HTTPException(status_code=500, detail=str(e))


class TeamOrder(BaseModel):
    ordered_ids: List[int]

@app.post("/team-members/reorder")
async def reorder_team_members(order: TeamOrder, user: dict = Depends(get_current_user)):
    try:
        for index, member_id in enumerate(order.ordered_ids):
            supabase.table('team_members').update({'display_order': index}).eq('id', member_id).execute()
        return {"message": "Team members reordered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Portfolio Category Management ---

@app.get("/portfolio-categories", response_model=List[PortfolioCategory])
async def get_portfolio_categories():
    try:
        response = supabase.table('portfolio_categories').select("*").execute()
        categories = []
        for item in response.data:
            category = {
                "id": item["id"],
                "name": item["name"]
            }
            categories.append(category)
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/portfolio-categories", response_model=PortfolioCategory)
async def create_portfolio_category(category: PortfolioCategoryIn, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('portfolio_categories').insert(category.dict()).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/portfolio-categories/{category_id}")
async def delete_portfolio_category(category_id: str, user: dict = Depends(get_current_user)):
    try:
        # Optional: Check if any project is using this category before deleting
        response = supabase.table('portfolio_categories').delete().eq("id", category_id).execute()
        return {"message": "Category deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Portfolio Project Management ---

@app.get("/portfolio-projects", response_model=List[PortfolioProject])
async def get_portfolio_projects(category_name: Optional[str] = None):
    try:
        query = supabase.table('portfolio_projects').select("*, portfolio_categories(name)").order('updated_at', desc=True)
        if category_name:
            query = query.eq('portfolio_categories.name', category_name)
        response = query.execute()

        # Map the response to the PortfolioProject model
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/portfolio-projects", response_model=PortfolioProject)
async def create_portfolio_project(project: PortfolioProjectIn, user: dict = Depends(get_current_user)):
    try:
        # Find or create category
        category_response = supabase.table('portfolio_categories').select("id").eq("name", project.category_name).single().execute()
        category_id = None
        if category_response.data:
            category_id = category_response.data["id"]
        else:
            new_category_response = supabase.table('portfolio_categories').insert({"name": project.category_name}).execute()
            category_id = new_category_response.data[0]["id"]

        project_data = project.dict()
        project_data["category_id"] = category_id
        del project_data["category_name"]

        # Serialize list fields to JSON strings if they are not None
        # if project_data.get("project_images") is not None:
        #     project_data["project_images"] = json.dumps(project_data["project_images"])
        # if project_data.get("technologies") is not None:
        #     project_data["technologies"] = json.dumps(project_data["technologies"])

        print(f"Project data before insert: {project_data}")
        response = supabase.table('portfolio_projects').insert(project_data).execute()
        
        # The response from Supabase contains the new project data, but without category_name.
        # We need to add it back to match the response_model.
        new_project = response.data[0]
        new_project["category_name"] = project.category_name
        
        return new_project
    except Exception as e:
        
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/portfolio-projects/{project_id}")
async def update_portfolio_project(project_id: str, project: PortfolioProjectIn, user: dict = Depends(get_current_user)):
    try:
        # Find or create category
        category_response = supabase.table('portfolio_categories').select("id").eq("name", project.category_name).single().execute()
        category_id = None
        if category_response.data:
            category_id = category_response.data["id"]
        else:
            new_category_response = supabase.table('portfolio_categories').insert({"name": project.category_name}).execute()
            category_id = new_category_response.data[0]["id"]

        project_data = project.dict(exclude_unset=True)
        project_data["category_id"] = category_id
        del project_data["category_name"]

        print(f"Project data before update: {project_data}")
        response = supabase.table('portfolio_projects').update(project_data).eq("id", project_id).execute()
        return response.data
    except Exception as e:
        
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/portfolio-projects/{project_id}")
async def delete_portfolio_project(project_id: str, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('portfolio_projects').delete().eq("id", project_id).execute()
        return {"message": "Project deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Order Management ---

def send_email_notification(order_details: dict):
    if not SENDER_EMAIL or not SENDER_EMAIL_PASSWORD or not RECEIVER_EMAIL:
        
        return

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"New Package Order: {order_details.get('package_name', 'N/A')}"

    body = f"""
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
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        pass

@app.post("/orders")
async def create_order(order: Order):
    try:
        order_data = order.dict()
        order_data['created_at'] = order_data['created_at'].isoformat()
        response = supabase.table('orders').insert(order_data).execute()
        if response.data:
            send_email_notification(order_data)
        return response.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/orders", response_model=List[Order])
async def get_all_orders(user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('orders').select("*, created_at").order("created_at", desc=True).execute()
        
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('orders').select("*").eq("order_id", order_id).single().execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/orders/{order_id}")
async def update_order_status(order_id: str, status: str, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('orders').update({"status": status}).eq("order_id", order_id).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/orders/{order_id}")
async def delete_order(order_id: str, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('orders').delete().eq("order_id", order_id).execute()
        return {"message": "Order deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Message Management ---

@app.get("/packages", response_model=List[PackageOut])
async def get_all_packages():
    try:
        response = supabase.table('packages').select("*").order("id").execute()
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/packages")
async def create_package(package: Package, user: dict = Depends(get_current_user)):
    try:
        package_data = package.dict()
        package_data["title"] = package_data.pop("name")
        response = supabase.table('packages').insert(package_data).execute()
        if response.data:
            return response.data
        else:
            raise HTTPException(status_code=400, detail=response.error.message if response.error else "Failed to create package in Supabase")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/packages/{package_id}")
async def update_package(package_id: str, package: Package, user: dict = Depends(get_current_user)):
    try:
        package_data = package.dict(exclude_unset=True)
        if "name" in package_data:
            package_data["title"] = package_data.pop("name")
        response = supabase.table('packages').update(package_data).eq("id", package_id).execute()
        if response.data:
            return response.data
        else:
            raise HTTPException(status_code=400, detail=response.error.message if response.error else "Failed to update package in Supabase")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/packages/{package_id}")
async def delete_package(package_id: str, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('packages').delete().eq("id", package_id).execute()
        return {"message": "Package deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Review Management ---

@app.post("/reviews", response_model=ReviewOut)
async def create_review(review: Review):
    try:
        review_data = review.dict()
        # Supabase will automatically set created_at and id
        response = supabase.table('reviews').insert(review_data).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/admin/reviews", response_model=List[ReviewOut])
async def get_all_reviews(user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('reviews').select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reviews", response_model=List[ReviewOut])
async def get_public_reviews():
    try:
        response = supabase.table('reviews').select("*").eq('approved', True).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/reviews/{review_id}", response_model=ReviewOut)
async def update_review(review_id: str, review: Review, user: dict = Depends(get_current_user)):
    try:
        review_data = review.dict(exclude_unset=True)
        response = supabase.table('reviews').update(review_data).eq('id', review_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Review with id {review_id} not found.")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/reviews/{review_id}/approve", response_model=ReviewOut)
async def approve_review(review_id: str, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('reviews').update({"approved": True}).eq("id", review_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Review with id {review_id} not found.")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/reviews/{review_id}")
async def delete_review(review_id: str, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('reviews').delete().eq("id", review_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Review with id {review_id} not found.")
        return {"message": "Review deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/messages", response_model=List[MessageOut])
async def get_all_messages(user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('messages').select("id, name, email, subject, message, read, received_at").order("received_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def send_new_message_email(message_details: dict):
    if not MESSAGE_SENDER_EMAIL or not MESSAGE_SENDER_EMAIL_PASSWORD or not RECEIVER_EMAIL:
        
        return

    msg = MIMEMultipart()
    msg['From'] = MESSAGE_SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    body = f"""
    You have received a new contact message!

    Name: {message_details.get('name', 'N/A')}
    Email: {message_details.get('email', 'N/A')}
    Subject: {message_details.get('subject', 'N/A')}
    Message:
    {message_details.get('message', 'N/A')}

    Received At: {message_details.get('received_at', 'N/A')}

    Please check the admin dashboard for more details and to reply.
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(MESSAGE_SENDER_EMAIL, MESSAGE_SENDER_EMAIL_PASSWORD)
            smtp.send_message(msg)
        
    except Exception as e:
        pass
        

@app.post("/messages")
async def create_message(message: MessageIn):
    try:
        message_data = message.dict()
        message_data['received_at'] = message_data['received_at'].isoformat()
        response = supabase.table('messages').insert(message_data).execute()
        if response.data:
            send_new_message_email(message_data) # Call email function
        return {"message": "Message sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/messages/{message_id}/read")
async def mark_message_as_read(message_id: str, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('messages').update({"read": True}).eq("id", message_id).execute()
        return {"message": "Message marked as read"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/messages/{message_id}")
async def delete_message(message_id: str, user: dict = Depends(get_current_user)):
    try:
        response = supabase.table('messages').delete().eq("id", message_id).execute()
        return {"message": "Message deleted successfully"}
    except Exception as e:
        pass

@app.post("/messages/reply")
async def reply_to_message(reply: ReplyMessage, user: dict = Depends(get_current_user)):
    if not MESSAGE_SENDER_EMAIL or not MESSAGE_SENDER_EMAIL_PASSWORD:
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
        return {"message": "Reply sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send reply: {e}")

@app.post("/send-reply-email") # New endpoint
async def send_reply_email(reply_data: SendReplyEmailRequest):
    if not MESSAGE_SENDER_EMAIL or not MESSAGE_SENDER_EMAIL_PASSWORD:
        raise HTTPException(status_code=500, detail="Email sending not configured in backend.")

    msg = MIMEMultipart()
    msg['From'] = MESSAGE_SENDER_EMAIL
    msg['To'] = reply_data.email
    msg['Subject'] = f"Re: {reply_data.subject or 'Your Message'}"

    body = f"""
    Dear {reply_data.name},

    {reply_data.replyBody}

    ---
    Original Message:
    From: {reply_data.name} <{reply_data.email}>
    Subject: {reply_data.subject or 'No Subject'}
    Message:
    {reply_data.originalMessage}
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(MESSAGE_SENDER_EMAIL, MESSAGE_SENDER_EMAIL_PASSWORD)
            smtp.send_message(msg)
        return {"message": "Reply sent successfully via backend."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send reply via backend: {e}")

# --- Image Upload ---
@app.post("/images/upload")
async def upload_image(file: Optional[UploadFile] = File(None), image_url: Optional[str] = Form(None)):
    if file:
        try:
            file_content = await file.read()
            # Use a generic bucket name, or make it dynamic if needed
            bucket_name = "images" 
            file_extension = file.filename.split(".")[-1]
            file_path = f"{uuid.uuid4()}.{file_extension}"

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
    elif image_url:
        return {"message": "Image URL received", "url": image_url}
    else:
        raise HTTPException(status_code=400, detail="No image file or URL provided.")