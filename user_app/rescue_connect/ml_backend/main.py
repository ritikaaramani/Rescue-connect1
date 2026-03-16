"""
FastAPI backend for ML-powered disaster image analysis.
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client

from app.image_analyzer import analyzer
from app.disaster_classifier import analyze_text, extract_entities
from app.ocr_pipeline import extract_text_from_url
from app.geo.geo_pipeline import resolve_location_async
from app.geo.extractor import extract_locations
from app.image_dedup import check_for_duplicate, compute_and_store_hash

load_dotenv()

app = FastAPI(
    title="RescueConnect ML Backend",
    description="ML-powered disaster image analysis API",
    version="1.0.0"
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL", ""),
    os.getenv("SUPABASE_SERVICE_KEY", "")
)


class AnalyzeRequest(BaseModel):
    image_url: str
    post_id: Optional[str] = None


class AnalyzeResponse(BaseModel):
    is_disaster: bool
    disaster_type: str
    severity: str
    description: str
    detected_elements: list
    location_hints: str
    people_affected: str
    urgency_score: int


class ProcessPostRequest(BaseModel):
    post_id: str


class UpdateStatusRequest(BaseModel):
    post_id: str
    status: str


class ResetAIRequest(BaseModel):
    post_id: str


class CheckDuplicateRequest(BaseModel):
    image_url: str
    hours_window: Optional[int] = 2


class CheckDuplicateResponse(BaseModel):
    is_duplicate: bool
    existing_post: Optional[dict] = None
    message: str


@app.get("/")
async def root():
    return {"message": "RescueConnect ML Backend is running", "status": "healthy"}


@app.get("/health")
async def health():
    return {"status": "healthy", "openai_configured": bool(analyzer.openai_key)}


@app.post("/check-duplicate", response_model=CheckDuplicateResponse)
async def check_duplicate(request: CheckDuplicateRequest):
    """
    Check if a similar image was uploaded within the specified time window.
    Used for deduplication before creating a new post.
    """
    if not request.image_url:
        raise HTTPException(status_code=400, detail="image_url is required")
    
    try:
        is_dup, existing = await check_for_duplicate(
            supabase, 
            request.image_url, 
            request.hours_window
        )
        
        if is_dup and existing:
            status_msg = existing.get("status", "pending")
            location = existing.get("location", "this area")
            disaster_type = existing.get("disaster_type", "disaster")
            
            if status_msg == "verified":
                message = f"This area has already been verified for {disaster_type}. Authorities are aware."
            elif status_msg == "dispatched":
                message = f"Help has already been dispatched to this area for {disaster_type}."
            elif status_msg == "urgent":
                message = f"This area is already marked as URGENT. Authorities have been alerted."
            else:
                message = f"A similar report from this area is already being processed."
            
            return CheckDuplicateResponse(
                is_duplicate=True,
                existing_post=existing,
                message=message
            )
        
        return CheckDuplicateResponse(
            is_duplicate=False,
            existing_post=None,
            message="No duplicate found. You can submit this report."
        )
    except Exception as e:
        print(f"Error checking duplicate: {e}")
        # On error, allow the upload to proceed
        return CheckDuplicateResponse(
            is_duplicate=False,
            existing_post=None,
            message="Could not check for duplicates. Proceeding with upload."
        )


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_image(request: AnalyzeRequest):
    """
    Analyze a single image and return disaster information.
    Does NOT update the database.
    """
    if not request.image_url:
        raise HTTPException(status_code=400, detail="image_url is required")
    
    result = await analyzer.analyze_image(request.image_url)
    return AnalyzeResponse(**result)


@app.post("/process-post")
async def process_post(request: ProcessPostRequest):
    """
    Process a post by ID:
    1. Fetch post from database
    2. Analyze the image
    3. Update the post with analysis results
    4. Compute and store image hash for deduplication
    """
    try:
        # Fetch the post
        response = supabase.table("posts").select("*").eq("id", request.post_id).single().execute()
        post = response.data
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if not post.get("image_url"):
            raise HTTPException(status_code=400, detail="Post has no image")
        
        # Compute and store image hash for deduplication
        image_hash = await compute_and_store_hash(supabase, request.post_id, post["image_url"])
        
        # Analyze the image
        analysis = await analyzer.analyze_image(post["image_url"])
        
        # Determine new status based on analysis
        new_status = "pending"
        if analysis["is_disaster"]:
            if analysis["urgency_score"] >= 7:
                new_status = "urgent"
            else:
                new_status = "verified"
        else:
            new_status = "rejected"  # Not a disaster image
        
        # Update the post with analysis results
        update_data = {
            "status": new_status,
            "disaster_type": analysis["disaster_type"],
            "severity": analysis["severity"],
            "ai_description": analysis["description"],
            "detected_elements": analysis["detected_elements"],
            "location_hints": analysis["location_hints"],
            "people_affected": analysis["people_affected"],
            "urgency_score": analysis["urgency_score"],
            "is_disaster": analysis["is_disaster"],
            "ai_processed": True,
            "image_hash": image_hash
        }
        
        supabase.table("posts").update(update_data).eq("id", request.post_id).execute()
        
        return {
            "success": True,
            "post_id": request.post_id,
            "new_status": new_status,
            "analysis": analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-full")
async def process_full_pipeline(request: ProcessPostRequest):
    """
    Full pipeline processing:
    1. Fetch post from DB
    2. Analyze image with Gemini (existing)
    3. Run OCR on image to extract text
    4. Run disaster_classifier on caption + OCR text
    5. Run geo_pipeline to infer location
    6. Update post with all results
    """
    try:
        # Fetch the post
        response = supabase.table("posts").select("*").eq("id", request.post_id).single().execute()
        post = response.data
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if not post.get("image_url"):
            raise HTTPException(status_code=400, detail="Post has no image")
        
        # Step 1: Analyze image with existing Gemini analyzer
        image_analysis = await analyzer.analyze_image(post["image_url"])
        
        # Step 2: Run OCR on image
        ocr_result = await extract_text_from_url(post["image_url"])
        pipeline_ocr_text = ocr_result.get("extracted_text", "")
        
        # Merge with AI visible text (fallback/enhancement)
        ai_visible_text = image_analysis.get("visible_text", "")
        ocr_text = f"{pipeline_ocr_text} {ai_visible_text}".strip()
        
        # Step 3: Run text analysis on caption + OCR text
        caption = post.get("caption", "")
        text_analysis = analyze_text(caption, ocr_text)
        
        # Step 4: Run geolocation pipeline
        extracted_locations = text_analysis.get("entities", {}).get("locations", [])
        
        # Check for User Verified GPS (Ground Truth)
        # If lat/lon exists and AI hasn't processed it yet, it's likely from the device/user
        user_gps = None
        if post.get("latitude") is not None and post.get("longitude") is not None:
            # Only treat as Ground Truth if not previously AI generated 
            # (or if we trust the input explicitly)
            if not post.get("ai_processed", False):
                user_gps = {"lat": post["latitude"], "lon": post["longitude"]}
        
        geo_result = await resolve_location_async(
            caption=caption,
            ocr_text=ocr_text,
            image_url=post["image_url"],
            extracted_locations=extracted_locations,
            location_hints=image_analysis.get("location_hints", []),
            gps=user_gps
        )
        
        # Determine status based on analysis
        new_status = "pending"
        if image_analysis["is_disaster"]:
            # Combine urgency from image and text analysis
            combined_urgency = max(
                image_analysis["urgency_score"],
                int(text_analysis.get("urgency_score", 0) * 10)
            )
            if combined_urgency >= 7:
                new_status = "urgent"
            else:
                new_status = "verified"
        else:
            new_status = "rejected"
        
        # Prepare update data with all results
        update_data = {
            # Existing fields
            "status": new_status,
            "disaster_type": image_analysis["disaster_type"],
            "severity": image_analysis["severity"],
            "ai_description": image_analysis["description"],
            "detected_elements": image_analysis["detected_elements"],
            "location_hints": image_analysis["location_hints"],
            "people_affected": image_analysis["people_affected"],
            "urgency_score": image_analysis["urgency_score"],
            "is_disaster": image_analysis["is_disaster"],
            "ai_processed": True,
            # New OCR fields
            "ocr_text": ocr_text if ocr_text else None,
            # New text analysis fields
            "text_labels": text_analysis.get("text_labels", []),
            "extracted_locations": extracted_locations,
            # New geolocation fields
            "inferred_latitude": geo_result.get("latitude"),
            "inferred_longitude": geo_result.get("longitude"),
            "location_confidence": geo_result.get("confidence"),
            "location_method": geo_result.get("method"),
            "scene_type": geo_result.get("scene_analysis", {}).get("scene_type") if geo_result.get("scene_analysis") else None
        }
        
        # Update the post
        supabase.table("posts").update(update_data).eq("id", request.post_id).execute()
        
        return {
            "success": True,
            "post_id": request.post_id,
            "new_status": new_status,
            "image_analysis": image_analysis,
            "ocr_result": {
                "extracted_text": ocr_text,
                "num_regions": ocr_result.get("num_regions", 0)
            },
            "text_analysis": text_analysis,
            "geo_result": geo_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DispatchUpdateRequest(BaseModel):
    post_id: str
    dispatch_status: str  # pending, assigned, in-progress, resolved
    assigned_team: Optional[str] = None
    resolution_notes: Optional[str] = None

# Valid status transitions
VALID_TRANSITIONS = {
    "pending": ["assigned"],
    "assigned": ["in-progress", "pending"],  # Allow rollback to pending
    "in-progress": ["resolved", "assigned"],  # Allow rollback to assigned
    "resolved": []  # Terminal state - no transitions allowed
}

@app.post("/update-dispatch")
async def update_dispatch(request: DispatchUpdateRequest):
    try:
        # Fetch current status
        result = supabase.table("posts").select("dispatch_status").eq("id", request.post_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Post not found")
        
        current_status = result.data[0].get("dispatch_status", "pending")
        new_status = request.dispatch_status
        
        # Validate transition
        if current_status != new_status:
            allowed = VALID_TRANSITIONS.get(current_status, [])
            if new_status not in allowed:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid transition: {current_status} → {new_status}. Allowed: {allowed}"
                )
        
        # Build update data
        data = {"dispatch_status": new_status}
        
        # Track timestamps
        from datetime import datetime
        if new_status == "assigned" and current_status == "pending":
            data["assigned_at"] = datetime.utcnow().isoformat()
        if new_status == "resolved":
            data["resolved_at"] = datetime.utcnow().isoformat()
        
        # Optional fields
        if request.assigned_team is not None:
            data["assigned_team"] = request.assigned_team
        if request.resolution_notes is not None:
            data["resolution_notes"] = request.resolution_notes
            
        supabase.table("posts").update(data).eq("id", request.post_id).execute()
        return {"success": True, "post_id": request.post_id, "new_status": new_status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update-status")
async def update_status(request: UpdateStatusRequest):
    """
    Update a post's status. Uses service key to bypass RLS.
    """
    try:
        valid_statuses = ["pending", "verified", "rejected", "urgent"]
        if request.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        supabase.table("posts").update({"status": request.status}).eq("id", request.post_id).execute()
        
        return {
            "success": True,
            "post_id": request.post_id,
            "new_status": request.status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset-ai")
async def reset_ai(request: ResetAIRequest):
    """
    Reset AI processing for a post so it can be reanalyzed.
    """
    try:
        supabase.table("posts").update({
            "ai_processed": False,
            "disaster_type": None,
            "severity": None,
            "ai_description": None,
            "detected_elements": None,
            "location_hints": None,
            "people_affected": None,
            "urgency_score": 0,
            "is_disaster": None
        }).eq("id", request.post_id).execute()
        
        return {
            "success": True,
            "post_id": request.post_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-all-pending")
async def process_all_pending():
    """
    Process all pending posts that haven't been analyzed yet.
    """
    try:
        # Fetch pending posts
        response = supabase.table("posts").select("*").eq("status", "pending").execute()
        posts = response.data or []
        
        results = []
        for post in posts:
            if not post.get("image_url"):
                continue
                
            try:
                # Analyze
                analysis = await analyzer.analyze_image(post["image_url"])
                
                # Determine status
                new_status = "pending"
                if analysis["is_disaster"]:
                    new_status = "urgent" if analysis["urgency_score"] >= 7 else "verified"
                else:
                    new_status = "rejected"
                
                # Update
                update_data = {
                    "status": new_status,
                    "disaster_type": analysis["disaster_type"],
                    "severity": analysis["severity"],
                    "ai_description": analysis["description"],
                    "detected_elements": analysis["detected_elements"],
                    "location_hints": analysis["location_hints"],
                    "people_affected": analysis["people_affected"],
                    "urgency_score": analysis["urgency_score"],
                    "is_disaster": analysis["is_disaster"],
                    "ai_processed": True
                }
                
                supabase.table("posts").update(update_data).eq("id", post["id"]).execute()
                
                results.append({
                    "post_id": post["id"],
                    "status": "processed",
                    "new_status": new_status
                })
                
            except Exception as e:
                results.append({
                    "post_id": post["id"],
                    "status": "failed",
                    "error": str(e)
                })
        
        return {
            "total_processed": len(results),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/compute-all-hashes")
async def compute_all_hashes():
    """
    Compute and store image hashes for all posts that don't have one yet.
    This is used to backfill hashes for existing posts.
    """
    try:
        # Fetch posts without image_hash
        response = supabase.table("posts")\
            .select("id, image_url")\
            .is_("image_hash", "null")\
            .not_.is_("image_url", "null")\
            .execute()
        
        posts = response.data or []
        results = []
        
        for post in posts:
            try:
                if post.get("image_url"):
                    image_hash = await compute_and_store_hash(
                        supabase, 
                        post["id"], 
                        post["image_url"]
                    )
                    results.append({
                        "post_id": post["id"],
                        "status": "success",
                        "hash": image_hash[:20] + "..." if image_hash else "failed"
                    })
            except Exception as e:
                results.append({
                    "post_id": post["id"],
                    "status": "failed",
                    "error": str(e)
                })
        
        return {
            "total_processed": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class NotificationRequest(BaseModel):
    post_id: str
    user_id: str
    status: str
    team_name: str = "Rescue Team"
    disaster_type: str = "Emergency"
    location: str = "your reported location"


@app.post("/send-notification")
async def send_notification(request: NotificationRequest):
    """
    Send email notification to user about dispatch status update.
    Uses Supabase to fetch user email and sends via Resend API.
    """
    import resend
    
    try:
        # Get user email from auth.users via Supabase Admin API
        # First get user profile to get display name
        profile_response = supabase.table("profiles")\
            .select("username, display_name")\
            .eq("id", request.user_id)\
            .single()\
            .execute()
        
        profile = profile_response.data or {}
        user_name = profile.get("display_name") or profile.get("username") or "User"
        
        # Get user email using Supabase Admin API
        user_email = None
        try:
            # Use Supabase admin client to get user email
            user_response = supabase.auth.admin.get_user_by_id(request.user_id)
            if user_response and user_response.user:
                user_email = user_response.user.email
        except Exception as e:
            print(f"Could not get user email: {e}")
        
        # Prepare email content
        status_messages = {
            "assigned": f"Good news! A rescue team ({request.team_name}) has been assigned to your emergency report.",
            "in-progress": f"Update: {request.team_name} is now actively responding to your emergency report.",
            "resolved": "Great news! Your reported emergency has been resolved. Thank you for helping your community stay safe."
        }
        
        message_body = f"""
Dear {user_name},

{status_messages.get(request.status, f"Your emergency report status has been updated to: {request.status}")}

📍 Location: {request.location}
🚨 Disaster Type: {request.disaster_type}
👥 Assigned Team: {request.team_name}
📊 Status: {request.status.replace('-', ' ').title()}

{"Our rescue team is on the way and will reach you as quickly as possible. Please stay safe and follow any local emergency guidelines." if request.status != "resolved" else ""}

If you need immediate assistance, please call your local emergency services.

Stay safe,
RescueConnect Emergency Response Team

---
This is an automated notification from RescueConnect.
"""
        
        # Try to send email via Resend if configured
        resend_api_key = os.getenv("RESEND_API_KEY")
        
        email_sent = False
        
        print(f"📧 Sending notification: user_email={user_email}, api_key_set={bool(resend_api_key)}")
        
        if resend_api_key and user_email:
            try:
                resend.api_key = resend_api_key
                
                # Must use onboarding@resend.dev for free tier (no domain verification)
                r = resend.Emails.send({
                    "from": "RescueConnect <onboarding@resend.dev>",
                    "to": [user_email],
                    "subject": f"🚨 RescueConnect: Rescue Team {request.status.replace('-', ' ').title()} for Your Report",
                    "text": message_body
                })
                
                email_sent = True
                print(f"✅ Email sent to {user_email} via Resend: {r}")
            except Exception as e:
                print(f"❌ Failed to send email via Resend: {e}")
        else:
            # Log the notification if email not configured
            print(f"📧 Notification (Resend API key not configured):")
            print(f"   To: {user_name} ({user_email or 'no email'})")
            print(f"   Status: {request.status}")
            print(f"   Team: {request.team_name}")
        
        return {
            "success": True,
            "user_name": user_name,
            "user_email": user_email,
            "email_sent": email_sent,
            "status": request.status,
            "message": f"Notification {'sent' if email_sent else 'logged'} for {user_name}"
        }
        
    except Exception as e:
        print(f"Error sending notification: {e}")
        # Return success anyway to not block the dispatch update
        return {
            "success": True,
            "email_sent": False,
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
