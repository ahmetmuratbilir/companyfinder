from fastapi import FastAPI, Depends, HTTPException, Query, status, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any, Set
import json
import base64
import os
from datetime import datetime
from contextlib import asynccontextmanager


from db import get_db, init_db, Lead, SearchConfig, Campaign, CampaignRecipient, SmtpSettings
from utils import calculate_lead_score
import asyncio
import random
from async_scraper import AsyncCompanyScraper
from fastapi.responses import StreamingResponse, HTMLResponse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Helper for SMTP password encryption/decryption
def encrypt_pw(plain: str) -> str:
    if not plain: return ""
    return base64.b64encode(plain.encode('utf-8')).decode('utf-8')

def decrypt_pw(enc: str) -> str:
    if not enc: return ""
    return base64.b64decode(enc.encode('utf-8')).decode('utf-8')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite Database on startup
    init_db()
    yield

app = FastAPI(
    title="Firma Bulma Botu & CRM API",
    description="FastAPI Backend for Lead Discovery, Quality Scoring, and Mail Campaigns",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Pydantic Schemas
# ==========================================

class SearchConfigBase(BaseModel):
    sector_name: str = Field(..., description="Sektör veya Klasör Adı")
    keywords: List[str] = Field(default_factory=list, description="Arama anahtar kelimeleri")
    cities: List[str] = Field(default_factory=list, description="İller")
    districts: List[str] = Field(default_factory=list, description="İlçeler")
    search_limit: int = Field(15, ge=1, le=100)
    delay_min: int = Field(15, ge=1)
    delay_max: int = Field(30, ge=1)
    blacklist_domains: List[str] = Field(default_factory=list, description="Hariç tutulacak alan adları")

class SearchConfigCreate(SearchConfigBase):
    pass

class SearchConfigOut(SearchConfigBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class LeadBase(BaseModel):
    company_name: str
    sector: str
    city: str
    district: str
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    lead_status: str = Field("yeni", description="yeni, incelendi, kampanyaya eklendi, mail gönderildi, cevap bekleniyor, kara liste")
    notes: Optional[str] = None

class LeadCreate(LeadBase):
    pass

class LeadOut(BaseModel):
    id: int
    company_name: str
    sector: str
    city: str
    district: str
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    score: int
    score_label: str
    score_breakdown_json: Optional[str] = None
    score_reason: Optional[str] = None
    lead_status: str
    notes: Optional[str] = None
    last_contacted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LeadsResponse(BaseModel):
    leads: List[LeadOut]
    total_count: int
    page: int
    limit: int

class LeadUpdate(BaseModel):
    lead_status: Optional[str] = None
    notes: Optional[str] = None
    company_name: Optional[str] = None
    sector: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None

class SmtpSettingsCreate(BaseModel):
    sender_email: EmailStr
    smtp_host: str
    smtp_port: int
    password: str = Field(..., description="SMTP şifresi veya Google Uygulama Şifresi")

class SmtpSettingsOut(BaseModel):
    id: int
    sender_email: str
    smtp_host: str
    smtp_port: int
    created_at: datetime

    class Config:
        from_attributes = True

class CampaignCreate(BaseModel):
    name: str
    subject: str
    template_html: str
    attachment_path: Optional[str] = None
    delay_min: int = Field(15, ge=1)
    delay_max: int = Field(30, ge=1)
    # List of Lead IDs to include or filter criteria
    lead_ids: Optional[List[int]] = None

class RecipientOut(BaseModel):
    id: int
    lead_id: int
    company_name: Optional[str] = None
    email: str
    status: str
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class CampaignOut(BaseModel):
    id: int
    name: str
    subject: str
    template_html: str
    attachment_path: Optional[str] = None
    delay_min: int
    delay_max: int
    status: str
    created_at: datetime
    recipient_count: int = 0
    sent_count: int = 0
    failed_count: int = 0

    class Config:
        from_attributes = True

class TestMailRequest(BaseModel):
    test_email: EmailStr
    subject: str
    body_html: str
    attachment_name: Optional[str] = None

# ==========================================
# Search Configs API
# ==========================================

@app.get("/api/search-configs", response_model=List[SearchConfigOut])
def list_search_configs(db: Session = Depends(get_db)):
    configs = db.query(SearchConfig).all()
    out = []
    for c in configs:
        out.append(SearchConfigOut(
            id=c.id,
            sector_name=c.sector_name,
            keywords=json.loads(c.keywords),
            cities=json.loads(c.cities),
            districts=json.loads(c.districts),
            search_limit=c.search_limit,
            delay_min=c.delay_min,
            delay_max=c.delay_max,
            blacklist_domains=json.loads(c.blacklist_domains),
            created_at=c.created_at
        ))
    return out

@app.post("/api/search-configs", response_model=SearchConfigOut)
def create_search_config(config_in: SearchConfigCreate, db: Session = Depends(get_db)):
    # Check if sector config already exists
    existing = db.query(SearchConfig).filter(SearchConfig.sector_name == config_in.sector_name).first()
    if existing:
        # Update instead of error
        existing.keywords = json.dumps(config_in.keywords)
        existing.cities = json.dumps(config_in.cities)
        existing.districts = json.dumps(config_in.districts)
        existing.search_limit = config_in.search_limit
        existing.delay_min = config_in.delay_min
        existing.delay_max = config_in.delay_max
        existing.blacklist_domains = json.dumps(config_in.blacklist_domains)
        db.commit()
        db.refresh(existing)
        c = existing
    else:
        c = SearchConfig(
            sector_name=config_in.sector_name,
            keywords=json.dumps(config_in.keywords),
            cities=json.dumps(config_in.cities),
            districts=json.dumps(config_in.districts),
            search_limit=config_in.search_limit,
            delay_min=config_in.delay_min,
            delay_max=config_in.delay_max,
            blacklist_domains=json.dumps(config_in.blacklist_domains)
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        
    return SearchConfigOut(
        id=c.id,
        sector_name=c.sector_name,
        keywords=json.loads(c.keywords),
        cities=json.loads(c.cities),
        districts=json.loads(c.districts),
        search_limit=c.search_limit,
        delay_min=c.delay_min,
        delay_max=c.delay_max,
        blacklist_domains=json.loads(c.blacklist_domains),
        created_at=c.created_at
    )

@app.delete("/api/search-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_search_config(config_id: int, db: Session = Depends(get_db)):
    config = db.query(SearchConfig).filter(SearchConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Arama ayarı bulunamadı.")
    db.delete(config)
    db.commit()
    return None

# ==========================================
# Leads API
# ==========================================

@app.get("/api/leads", response_model=LeadsResponse)
def list_leads(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    sector: Optional[str] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100)
):
    query = db.query(Lead)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Lead.company_name.like(search_filter)) | 
            (Lead.email.like(search_filter)) | 
            (Lead.website.like(search_filter)) |
            (Lead.phone.like(search_filter))
        )
    
    if status:
        query = query.filter(Lead.lead_status == status)
    if sector:
        query = query.filter(Lead.sector == sector)
    if city:
        query = query.filter(Lead.city == city)
    if district:
        query = query.filter(Lead.district == district)
    if min_score is not None:
        query = query.filter(Lead.score >= min_score)
    if max_score is not None:
        query = query.filter(Lead.score <= max_score)
        
    total_count = query.count()
    offset = (page - 1) * limit
    leads = query.order_by(Lead.score.desc()).offset(offset).limit(limit).all()
    
    return {
        "leads": leads,
        "total_count": total_count,
        "page": page,
        "limit": limit
    }

@app.get("/api/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Firma bulunamadı.")
    return lead

@app.post("/api/leads", response_model=LeadOut)
def create_lead(lead_in: LeadCreate, db: Session = Depends(get_db)):
    # Calculate Lead score
    lead_dict = lead_in.dict()
    # Mock some properties that scraper extracts to score properly
    lead_dict['alim_yapma_durumu'] = "Belirsiz / Bilgi Yok" # default manual entry
    score_details = calculate_lead_score(lead_dict)
    
    lead = Lead(
        company_name=lead_in.company_name,
        sector=lead_in.sector,
        city=lead_in.city,
        district=lead_in.district,
        website=lead_in.website,
        email=lead_in.email,
        phone=lead_in.phone,
        description=lead_in.description,
        source_url=lead_in.source_url,
        lead_status=lead_in.lead_status,
        notes=lead_in.notes,
        score=score_details['score'],
        score_label=score_details['score_label'],
        score_breakdown_json=score_details['score_breakdown_json'],
        score_reason=score_details['score_reason']
    )
    
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead

@app.put("/api/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, lead_in: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Firma bulunamadı.")
    
    update_data = lead_in.dict(exclude_unset=True)
    
    # Check if fields that affect scoring are changed
    recalculate_needed = False
    scoring_fields = ['website', 'email', 'phone', 'description', 'sector', 'city', 'district']
    for field in scoring_fields:
        if field in update_data and getattr(lead, field) != update_data[field]:
            recalculate_needed = True
            
    for key, value in update_data.items():
        setattr(lead, key, value)
        
    if recalculate_needed:
        # Pass current model values to dictionary for recalculation
        lead_dict = {
            'website': lead.website,
            'email': lead.email,
            'phone': lead.phone,
            'description': lead.description,
            'district': lead.district,
            'alim_yapma_durumu': "Belirsiz / Bilgi Yok", # standard mock
            'sector': lead.sector
        }
        score_details = calculate_lead_score(lead_dict)
        lead.score = score_details['score']
        lead.score_label = score_details['score_label']
        lead.score_breakdown_json = score_details['score_breakdown_json']
        lead.score_reason = score_details['score_reason']
        
    db.commit()
    db.refresh(lead)
    return lead

@app.delete("/api/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Firma bulunamadı.")
    db.delete(lead)
    db.commit()
    return None

# ==========================================
# SMTP Settings API
# ==========================================

@app.get("/api/smtp-settings", response_model=Optional[SmtpSettingsOut])
def get_smtp_settings(db: Session = Depends(get_db)):
    settings = db.query(SmtpSettings).first()
    if not settings:
        return None
    return settings

@app.post("/api/smtp-settings", response_model=SmtpSettingsOut)
def save_smtp_settings(settings_in: SmtpSettingsCreate, db: Session = Depends(get_db)):
    existing = db.query(SmtpSettings).first()
    enc_pass = encrypt_pw(settings_in.password)
    
    if existing:
        existing.sender_email = settings_in.sender_email
        existing.smtp_host = settings_in.smtp_host
        existing.smtp_port = settings_in.smtp_port
        existing.encrypted_password = enc_pass
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_settings = SmtpSettings(
            sender_email=settings_in.sender_email,
            smtp_host=settings_in.smtp_host,
            smtp_port=settings_in.smtp_port,
            encrypted_password=enc_pass
        )
        db.add(new_settings)
        db.commit()
        db.refresh(new_settings)
        return new_settings

# ==========================================
# Campaigns API
# ==========================================

@app.get("/api/campaigns", response_model=List[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)):
    campaigns = db.query(Campaign).all()
    out = []
    for c in campaigns:
        # Calculate counts
        rec_count = db.query(CampaignRecipient).filter(CampaignRecipient.campaign_id == c.id).count()
        sent_count = db.query(CampaignRecipient).filter(
            CampaignRecipient.campaign_id == c.id, 
            CampaignRecipient.status == "sent"
        ).count()
        failed_count = db.query(CampaignRecipient).filter(
            CampaignRecipient.campaign_id == c.id, 
            CampaignRecipient.status == "failed"
        ).count()
        
        out.append(CampaignOut(
            id=c.id,
            name=c.name,
            subject=c.subject,
            template_html=c.template_html,
            attachment_path=c.attachment_path,
            delay_min=c.delay_min,
            delay_max=c.delay_max,
            status=c.status,
            created_at=c.created_at,
            recipient_count=rec_count,
            sent_count=sent_count,
            failed_count=failed_count
        ))
    return out

@app.post("/api/campaigns", response_model=CampaignOut)
def create_campaign(camp_in: CampaignCreate, db: Session = Depends(get_db)):
    # Create Campaign Record
    camp = Campaign(
        name=camp_in.name,
        subject=camp_in.subject,
        template_html=camp_in.template_html,
        attachment_path=camp_in.attachment_path,
        delay_min=camp_in.delay_min,
        delay_max=camp_in.delay_max,
        status="pending"
    )
    db.add(camp)
    db.commit()
    db.refresh(camp)
    
    # Populate recipients
    added_recipients = 0
    
    if camp_in.lead_ids:
        # Add specified leads
        leads_to_add = db.query(Lead).filter(Lead.id.in_(camp_in.lead_ids)).all()
    else:
        # Default: auto-select leads with high quality score (score >= 80) and having emails, status is 'yeni'
        # Also exclude blacklisted leads
        leads_to_add = db.query(Lead).filter(
            Lead.email.isnot(None),
            Lead.email != "",
            Lead.email != "Belirsiz / Bilgi Yok",
            Lead.score >= 80,
            Lead.lead_status == "yeni"
        ).all()
        
    for lead in leads_to_add:
        # Check if already added to a running/completed campaign to prevent spam (deduplication)
        # We check if there's any campaign recipient for this lead where status is sent/pending
        already_exists = db.query(CampaignRecipient).filter(
            CampaignRecipient.lead_id == lead.id,
            CampaignRecipient.status.in_(["pending", "sent"])
        ).first()
        
        if already_exists:
            continue
            
        # Add to recipients queue
        recipient = CampaignRecipient(
            campaign_id=camp.id,
            lead_id=lead.id,
            email=lead.email,
            status="pending"
        )
        db.add(recipient)
        
        # Update CRM Lead Status to 'kampanyaya eklendi'
        lead.lead_status = "kampanyaya eklendi"
        added_recipients += 1
        
    db.commit()
    
    return CampaignOut(
        id=camp.id,
        name=camp.name,
        subject=camp.subject,
        template_html=camp.template_html,
        attachment_path=camp.attachment_path,
        delay_min=camp.delay_min,
        delay_max=camp.delay_max,
        status=camp.status,
        created_at=camp.created_at,
        recipient_count=added_recipients,
        sent_count=0,
        failed_count=0
    )

@app.get("/api/campaigns/{campaign_id}", response_model=Dict[str, Any])
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadı.")
        
    recipients = db.query(CampaignRecipient).filter(CampaignRecipient.campaign_id == campaign_id).all()
    
    rec_list = []
    for r in recipients:
        lead = db.query(Lead).filter(Lead.id == r.lead_id).first()
        rec_list.append({
            "id": r.id,
            "lead_id": r.lead_id,
            "company_name": lead.company_name if lead else "Bilinmeyen Firma",
            "email": r.email,
            "status": r.status,
            "sent_at": r.sent_at,
            "error_message": r.error_message
        })
        
    rec_count = len(rec_list)
    sent_count = sum(1 for r in rec_list if r['status'] == "sent")
    failed_count = sum(1 for r in rec_list if r['status'] == "failed")
    
    return {
        "campaign": {
            "id": campaign.id,
            "name": campaign.name,
            "subject": campaign.subject,
            "template_html": campaign.template_html,
            "attachment_path": campaign.attachment_path,
            "delay_min": campaign.delay_min,
            "delay_max": campaign.delay_max,
            "status": campaign.status,
            "created_at": campaign.created_at,
            "recipient_count": rec_count,
            "sent_count": sent_count,
            "failed_count": failed_count
        },
        "recipients": rec_list
    }

@app.delete("/api/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadı.")
    
    # Reset lead statuses from 'kampanyaya eklendi' or 'pending' back to 'yeni'
    for r in campaign.recipients:
        lead = db.query(Lead).filter(Lead.id == r.lead_id).first()
        if lead and lead.lead_status == "kampanyaya eklendi":
            lead.lead_status = "yeni"
            
    db.delete(campaign)
    db.commit()
    return None

active_campaign_tasks = {}

async def run_campaign_worker(campaign_id: int, db_session_factory):
    db = db_session_factory()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return
            
        smtp = db.query(SmtpSettings).first()
        if not smtp:
            campaign.status = "failed"
            db.commit()
            return
            
        sender_email = smtp.sender_email
        smtp_host = smtp.smtp_host
        smtp_port = smtp.smtp_port
        password = decrypt_pw(smtp.encrypted_password)
        
        attachment_path = campaign.attachment_path
        resolved_cv_path = None
        if attachment_path:
            possible_paths = [
                attachment_path,
                os.path.join(os.path.dirname(os.path.abspath(__file__)), attachment_path),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), attachment_path)
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    resolved_cv_path = p
                    break
                    
        recipients = db.query(CampaignRecipient).filter(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.status == "pending"
        ).all()
        
        campaign.status = "running"
        db.commit()
        
        for idx, rec in enumerate(recipients):
            # Refresh to check if paused
            db.refresh(campaign)
            if campaign.status != "running":
                return
                
            lead = db.query(Lead).filter(Lead.id == rec.lead_id).first()
            if not lead:
                continue
                
            # Render template variables
            body_content = campaign.template_html
            body_content = body_content.replace("{firma_adi}", lead.company_name)
            body_content = body_content.replace("{sektor}", lead.sector)
            body_content = body_content.replace("{il}", lead.city)
            body_content = body_content.replace("{ilce}", lead.district)
            
            try:
                def send_mail_sync():
                    msg = MIMEMultipart()
                    msg['From'] = sender_email
                    msg['To'] = rec.email
                    msg['Subject'] = campaign.subject
                    
                    msg.attach(MIMEText(body_content, 'html', 'utf-8'))
                    
                    if resolved_cv_path:
                        filename = os.path.basename(resolved_cv_path)
                        with open(resolved_cv_path, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename= "{filename}"')
                            msg.attach(part)
                            
                    server = smtplib.SMTP(smtp_host, smtp_port)
                    server.starttls()
                    server.login(sender_email, password)
                    server.sendmail(sender_email, rec.email, msg.as_string())
                    server.quit()
                    
                await asyncio.to_thread(send_mail_sync)
                rec.status = "sent"
                rec.sent_at = datetime.utcnow()
                lead.lead_status = "mail gönderildi"
                lead.last_contacted_at = datetime.utcnow()
            except Exception as e:
                rec.status = "failed"
                rec.error_message = str(e)
                lead.lead_status = "incelendi"
                
            db.commit()
            
            if idx < len(recipients) - 1:
                db.refresh(campaign)
                if campaign.status != "running":
                    return
                delay = random.uniform(campaign.delay_min, campaign.delay_max)
                await asyncio.sleep(delay)
                
        campaign.status = "completed"
        db.commit()
        
    except Exception:
        if campaign:
            campaign.status = "paused"
            db.commit()
    finally:
        db.close()
        if campaign_id in active_campaign_tasks:
            del active_campaign_tasks[campaign_id]

# --- Campaign status update API ---

@app.put("/api/campaigns/{campaign_id}/status")
async def update_campaign_status(campaign_id: int, status_update: Dict[str, str], db: Session = Depends(get_db)):
    global active_campaign_tasks
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadı.")
        
    new_status = status_update.get("status")
    if new_status not in ["running", "paused", "completed"]:
        raise HTTPException(status_code=400, detail="Geçersiz kampanya durumu.")
        
    campaign.status = new_status
    db.commit()
    
    if new_status == "running" and campaign_id not in active_campaign_tasks:
        from db import SessionLocal
        active_campaign_tasks[campaign_id] = asyncio.create_task(
            run_campaign_worker(campaign_id, SessionLocal)
        )
        
    return {"id": campaign.id, "status": campaign.status}

@app.post("/api/smtp-settings/test")
async def send_test_mail(payload: TestMailRequest, db: Session = Depends(get_db)):
    smtp = db.query(SmtpSettings).first()
    if not smtp:
        raise HTTPException(status_code=400, detail="SMTP ayarları tanımlanmamış.")
        
    sender_email = smtp.sender_email
    smtp_host = smtp.smtp_host
    smtp_port = smtp.smtp_port
    password = decrypt_pw(smtp.encrypted_password)
    
    resolved_cv_path = None
    if payload.attachment_name:
        possible_paths = [
            payload.attachment_name,
            os.path.join(os.path.dirname(os.path.abspath(__file__)), payload.attachment_name),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), payload.attachment_name)
        ]
        for p in possible_paths:
            if os.path.exists(p):
                resolved_cv_path = p
                break
                
    try:
        def test_send():
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = payload.test_email
            msg['Subject'] = f"[TEST] {payload.subject}"
            
            msg.attach(MIMEText(payload.body_html, 'html', 'utf-8'))
            
            if resolved_cv_path:
                filename = os.path.basename(resolved_cv_path)
                with open(resolved_cv_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename= "{filename}"')
                    msg.attach(part)
                    
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, payload.test_email, msg.as_string())
            server.quit()
            
        await asyncio.to_thread(test_send)
        return {"message": "Test maili başarıyla gönderildi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMTP Gönderim Hatası: {str(e)}")

# ==========================================
# Scraper Integration (Phase 2)
# ==========================================

class ActiveLogger:
    def __init__(self):
        self.connections: Set[asyncio.Queue] = set()
        
    def log(self, message: str, level: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = json.dumps({"timestamp": timestamp, "message": message, "level": level})
        for q in list(self.connections):
            try:
                q.put_nowait(log_entry)
            except Exception:
                pass
            
    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.connections.add(q)
        return q
        
    def unsubscribe(self, q: asyncio.Queue):
        if q in self.connections:
            self.connections.remove(q)

scraper_logger = ActiveLogger()

scrape_status = {
    "is_running": False,
    "current_sector": None,
    "total_found": 0,
    "total_processed": 0,
    "progress_percent": 0
}
active_scrape_task = None

async def background_scrape_task(config_id: int, db_session_factory):
    global scrape_status
    db = db_session_factory()
    try:
        config = db.query(SearchConfig).filter(SearchConfig.id == config_id).first()
        if not config:
            scraper_logger.log(f"Hata: Arama ayarı bulunamadı (ID: {config_id})", "error")
            scrape_status["is_running"] = False
            return
            
        sector_name = config.sector_name
        keywords = json.loads(config.keywords)
        cities = json.loads(config.cities)
        limit = config.search_limit
        delay_min = config.delay_min
        delay_max = config.delay_max
        blacklist = json.loads(config.blacklist_domains)
        
        scraper_logger.log(f"Tarama başlatılıyor: Sektör={sector_name}, Şehirler={cities}", "info")
        
        scraper = AsyncCompanyScraper(blacklist=blacklist)
        
        scrape_status["is_running"] = True
        scrape_status["current_sector"] = sector_name
        scrape_status["total_found"] = 0
        scrape_status["total_processed"] = 0
        scrape_status["progress_percent"] = 0
        
        # 1. Discover potential companies
        discovered_companies = []
        for city in cities:
            for keyword in keywords:
                # Check cancellation
                if not scrape_status["is_running"]:
                    scraper_logger.log("Tarama kullanıcı tarafından durduruldu.", "warning")
                    return
                    
                scraper_logger.log(f"Arama yapılıyor: Şehir='{city}', Sorgu='{keyword}'", "info")
                results = await scraper.discover_companies_by_query(keyword, city, limit=limit)
                discovered_companies.extend(results)
                
                # Cooldown
                await asyncio.sleep(random.uniform(1.5, 3.0))
                
        # Deduplicate
        unique_companies = []
        seen_sites = set()
        for c in discovered_companies:
            site = c.get('website')
            if site and site not in seen_sites:
                seen_sites.add(site)
                unique_companies.append(c)
                
        scraper_logger.log(f"Arama tamamlandı. Toplam {len(discovered_companies)} aday arasından {len(unique_companies)} benzersiz firma tespit edildi.", "info")
        scrape_status["total_found"] = len(unique_companies)
        
        if not unique_companies:
            scraper_logger.log("Arama kriterlerine uygun firma bulunamadı.", "warning")
            scrape_status["is_running"] = False
            return
            
        # 2. Enrich and Score Leads
        for i, company in enumerate(unique_companies):
            if not scrape_status["is_running"]:
                scraper_logger.log("Tarama kullanıcı tarafından durduruldu.", "warning")
                return
                
            name = company['name']
            website = company['website']
            
            scraper_logger.log(f"[{i+1}/{len(unique_companies)}] Web sitesi inceleniyor: {name} ({website})", "info")
            
            # Enrich web data
            try:
                enriched = await scraper.enrich_company_data(company)
            except Exception as e:
                scraper_logger.log(f"{name} incelenirken hata oluştu: {e}", "warning")
                enriched = company
                enriched['error'] = str(e)
                
            # Score Lead
            lead_dict = {
                'website': website,
                'email': enriched.get('email', ''),
                'phone': enriched.get('phone', ''),
                'description': enriched.get('summary', ''),
                'district': enriched.get('district', 'Unknown'),
                'alim_yapma_durumu': enriched.get('alim_yapma_durumu', 'Belirsiz / Bilgi Yok'),
                'sector': sector_name
            }
            score_details = calculate_lead_score(lead_dict)
            
            # Save or Update in DB
            existing_lead = None
            if website:
                existing_lead = db.query(Lead).filter(Lead.website == website).first()
            if not existing_lead:
                existing_lead = db.query(Lead).filter(Lead.company_name == name, Lead.city == company['city']).first()
                
            if existing_lead:
                # Update
                existing_lead.email = enriched.get('email') or existing_lead.email
                existing_lead.phone = enriched.get('phone') or existing_lead.phone
                existing_lead.description = enriched.get('summary') or existing_lead.description
                existing_lead.sector = sector_name
                existing_lead.score = score_details['score']
                existing_lead.score_label = score_details['score_label']
                existing_lead.score_breakdown_json = score_details['score_breakdown_json']
                existing_lead.score_reason = score_details['score_reason']
                scraper_logger.log(f"Güncellendi: {name} | Skor: {score_details['score']} ({score_details['score_label']})", "success")
            else:
                # Add
                new_lead = Lead(
                    company_name=name,
                    sector=sector_name,
                    city=company['city'],
                    district=enriched.get('district', 'Unknown'),
                    website=website or None,
                    email=enriched.get('email') or None,
                    phone=enriched.get('phone') or None,
                    description=enriched.get('summary') or None,
                    score=score_details['score'],
                    score_label=score_details['score_label'],
                    score_breakdown_json=score_details['score_breakdown_json'],
                    score_reason=score_details['score_reason'],
                    lead_status="yeni"
                )
                db.add(new_lead)
                scraper_logger.log(f"Eklendi: {name} | Skor: {score_details['score']} ({score_details['score_label']})", "success")
                
            db.commit()
            
            # Update status
            scrape_status["total_processed"] += 1
            scrape_status["progress_percent"] = int((i + 1) / len(unique_companies) * 100)
            
            # Bot-safe Delay
            delay = random.uniform(delay_min, delay_max)
            scraper_logger.log(f"{delay:.1f} saniye bekleniyor...", "info")
            await asyncio.sleep(delay)
            
        scraper_logger.log("Tarama işlemi başarıyla tamamlandı!", "success")
        scrape_status["is_running"] = False
        scrape_status["current_sector"] = None
        
    except asyncio.CancelledError:
        scraper_logger.log("Tarama işlemi iptal edildi.", "warning")
        scrape_status["is_running"] = False
        scrape_status["current_sector"] = None
    except Exception as e:
        scraper_logger.log(f"Sistem Hatası: {e}", "error")
        scrape_status["is_running"] = False
        scrape_status["current_sector"] = None
    finally:
        db.close()

# --- Scraper API Endpoints ---

@app.get("/api/scrape/status")
async def get_scraper_status():
    return scrape_status

@app.post("/api/scrape/start")
async def start_scraper(payload: Dict[str, int], db: Session = Depends(get_db)):
    global active_scrape_task
    config_id = payload.get("config_id")
    if not config_id:
        raise HTTPException(status_code=400, detail="config_id parametresi gereklidir.")
        
    if scrape_status["is_running"]:
        raise HTTPException(status_code=400, detail="Hali hazırda aktif bir tarama işlemi yürütülüyor.")
        
    config = db.query(SearchConfig).filter(SearchConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Arama ayarı bulunamadı.")
        
    from db import SessionLocal
    active_scrape_task = asyncio.create_task(background_scrape_task(config_id, SessionLocal))
    return {"message": "Tarama başlatıldı.", "status": scrape_status}

@app.post("/api/scrape/stop")
async def stop_scraper():
    global active_scrape_task
    if not scrape_status["is_running"]:
        return {"message": "Aktif bir tarama bulunmamaktadır."}
        
    scrape_status["is_running"] = False
    if active_scrape_task:
        active_scrape_task.cancel()
        active_scrape_task = None
        
    scraper_logger.log("Tarama kullanıcı isteğiyle durduruldu.", "warning")
    return {"message": "Tarama durduruldu."}

@app.get("/api/scrape/stream")
async def stream_scraper_logs():
    q = scraper_logger.subscribe()
    
    async def log_generator():
        try:
            # Yield initial connection message
            yield f"data: {json.dumps({'message': 'Canlı konsol bağlantısı kuruldu.', 'level': 'info'})}\n\n"
            while True:
                log_entry = await q.get()
                yield f"data: {log_entry}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            scraper_logger.unsubscribe(q)
            
    return StreamingResponse(log_generator(), media_type="text/event-stream")

# ==========================================
# Static Files Serving (Phase 3)
# ==========================================
import os

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/style.css")
async def read_css():
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        return Response(content=f.read(), media_type="text/css")

@app.get("/app.js")
async def read_js():
    js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "app.js")
    with open(js_path, "r", encoding="utf-8") as f:
        return Response(content=f.read(), media_type="application/javascript")

if __name__ == "__main__":
    import uvicorn
    # Start the server on port 8000
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
