from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import datetime
import os

Base = declarative_base()

# 1. SearchConfig Model
class SearchConfig(Base):
    __tablename__ = 'search_configs'
    
    id = Column(Integer, primary_key=True)
    sector_name = Column(String(100), unique=True, nullable=False)
    keywords = Column(Text, nullable=False)  # JSON string of tags
    cities = Column(Text, nullable=False)    # JSON string of cities
    districts = Column(Text, nullable=False) # JSON string of districts
    search_limit = Column(Integer, default=15)
    delay_min = Column(Integer, default=15)
    delay_max = Column(Integer, default=30)
    blacklist_domains = Column(Text, nullable=False) # JSON string
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# 2. Lead Model (CRM & Scoring)
class Lead(Base):
    __tablename__ = 'leads'
    
    id = Column(Integer, primary_key=True)
    company_name = Column(String(200), nullable=False)
    sector = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    website = Column(String(250), nullable=True)
    email = Column(String(150), nullable=True)
    phone = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    source_url = Column(String(250), nullable=True)
    score = Column(Integer, default=0)
    score_label = Column(String(50), default="Düşük Kalite")  # Güçlü / Orta / Zayıf / Düşük Kalite
    score_breakdown_json = Column(Text, nullable=True)        # Breakdown in JSON
    score_reason = Column(Text, nullable=True)                 # Short text explanation of the score
    lead_status = Column(String(50), default="yeni")          # yeni, incelendi, kampanyaya eklendi, mail gönderildi, cevap bekleniyor, kara liste
    notes = Column(Text, nullable=True)                       # Manuel user notes
    last_contacted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# 3. Campaign Model
class Campaign(Base):
    __tablename__ = 'campaigns'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    subject = Column(String(250), nullable=False)
    template_html = Column(Text, nullable=False)
    attachment_path = Column(String(250), nullable=True)
    delay_min = Column(Integer, default=15)
    delay_max = Column(Integer, default=30)
    status = Column(String(50), default="pending")            # pending, running, paused, completed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    recipients = relationship("CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")

# 4. CampaignRecipient Model
class CampaignRecipient(Base):
    __tablename__ = 'campaign_recipients'
    
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=False)
    lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False)
    email = Column(String(150), nullable=False)
    status = Column(String(50), default="pending")            # pending, sent, failed
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    campaign = relationship("Campaign", back_populates="recipients")

# 5. SmtpSettings Model
class SmtpSettings(Base):
    __tablename__ = 'smtp_settings'
    
    id = Column(Integer, primary_key=True)
    sender_email = Column(String(150), unique=True, nullable=False)
    smtp_host = Column(String(150), nullable=False)
    smtp_port = Column(Integer, nullable=False)
    encrypted_password = Column(String(200), nullable=False)  # Encrypted password
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Database session setup
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    print(f"SQLite veritabanı başarıyla oluşturuldu: {DB_PATH}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
