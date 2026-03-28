from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///jakala_cc.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'cc_users'
    id               = Column(Integer, primary_key=True)
    name             = Column(String(100), nullable=False)
    email            = Column(String(200), unique=True, nullable=False)
    password_hash    = Column(String(200), nullable=False)
    role             = Column(String(20), nullable=False)   # 'country_head' | 'global'
    country          = Column(String(5))                    # 'no','dk','se','uk','fr' | None
    initials         = Column(String(3))
    created_at       = Column(DateTime, default=datetime.utcnow)

class Industry(Base):
    __tablename__ = 'cc_industries'
    id          = Column(Integer, primary_key=True)
    name        = Column(String(100), nullable=False)
    slug        = Column(String(50), unique=True, nullable=False)
    icon        = Column(String(10))
    accounts    = relationship('Account', back_populates='industry_rel')

class Account(Base):
    __tablename__ = 'cc_accounts'
    id               = Column(Integer, primary_key=True)
    name             = Column(String(200), nullable=False)
    slug             = Column(String(100))
    country          = Column(String(5), nullable=False)
    industry_id      = Column(Integer, ForeignKey('cc_industries.id'))
    account_type     = Column(String(20), default='prospect')  # 'prospect' | 'existing'
    icp_score        = Column(Float)
    deal_score       = Column(Float)
    pipeline_value   = Column(Float)
    win_probability  = Column(Float)
    named_buyer      = Column(String(200))
    buyer_role       = Column(String(150))
    revenue          = Column(String(50))
    tech_stack       = Column(Text)
    notes            = Column(Text)
    created_at       = Column(DateTime, default=datetime.utcnow)
    industry_rel     = relationship('Industry', back_populates='accounts')
    activations      = relationship('Activation', back_populates='account', cascade='all, delete-orphan')
    predictions      = relationship('Prediction', back_populates='account', cascade='all, delete-orphan')

class Service(Base):
    __tablename__ = 'cc_services'
    id                   = Column(Integer, primary_key=True)
    name                 = Column(String(200), nullable=False)
    slug                 = Column(String(100), unique=True)
    short_name           = Column(String(60))
    practice             = Column(String(60))   # 'Commerce' | 'Data & AI' | 'Growth'
    color                = Column(String(20))   # hex
    entry_price_min      = Column(Float)
    entry_price_max      = Column(Float)
    expansion_price_min  = Column(Float)
    expansion_price_max  = Column(Float)
    activations          = relationship('Activation', back_populates='service')

class Activation(Base):
    __tablename__ = 'cc_activations'
    id               = Column(Integer, primary_key=True)
    account_id       = Column(Integer, ForeignKey('cc_accounts.id'))
    service_id       = Column(Integer, ForeignKey('cc_services.id'))
    manager          = Column(String(100))
    stage            = Column(String(30), default='identified')
    # 'identified' | 'proposed' | 'negotiating' | 'active' | 'completed'
    cost_estimate    = Column(Float)
    timeline_weeks   = Column(Integer)
    roi_estimate     = Column(Float)
    milestones       = Column(Text)   # JSON
    notes            = Column(Text)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    account          = relationship('Account', back_populates='activations')
    service          = relationship('Service', back_populates='activations')

class Signal(Base):
    __tablename__ = 'cc_signals'
    id                   = Column(Integer, primary_key=True)
    country              = Column(String(5))   # None = global
    vertical             = Column(String(100))
    signal_type          = Column(String(50))
    # 'regulation' | 'politics' | 'market' | 'technology' | 'competitor'
    severity             = Column(String(20))  # 'critical' | 'warning' | 'info'
    title                = Column(String(300))
    description          = Column(Text)
    action_recommended   = Column(Text)
    source               = Column(String(200))
    date                 = Column(DateTime, default=datetime.utcnow)
    is_active            = Column(Boolean, default=True)

class Prediction(Base):
    __tablename__ = 'cc_predictions'
    id                      = Column(Integer, primary_key=True)
    account_id              = Column(Integer, ForeignKey('cc_accounts.id'))
    country                 = Column(String(5))
    vertical                = Column(String(100))
    risk_score              = Column(Float)         # 0–10
    opportunity_score       = Column(Float)         # 0–10
    trigger_summary         = Column(Text)
    recommended_service_id  = Column(Integer, ForeignKey('cc_services.id'))
    confidence              = Column(Float)         # 0–1
    timeframe_weeks         = Column(Integer)
    generated_at            = Column(DateTime, default=datetime.utcnow)
    account                 = relationship('Account', back_populates='predictions')
    recommended_service     = relationship('Service')

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
