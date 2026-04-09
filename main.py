from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import List, Optional
import json
from expense_algo import minimize_debts

# ==========================================
# 1. 資料庫設定 (雲端 Supabase - 終極穩定版)
# ==========================================
# 換回 6543 閘道，支援 Render 的 IPv4 網路環境
SQLALCHEMY_DATABASE_URL = "postgresql://postgres.dyckcsvjlpsepyriiwqz:0214iris19780922@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"

# 加入 pool_pre_ping=True 確保雲端連線穩定不斷線
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DBItinerary(Base):
    __tablename__ = "itineraries"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)
    start_time = Column(String)
    end_time = Column(String)
    location = Column(String)
    notes = Column(String, default="")
    map_url = Column(String, default="")

class DBExpense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String)
    amount = Column(Integer)
    payer = Column(String)
    shared_by = Column(String)

class DBMember(Base): 
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

class DBSetting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(String)

Base.metadata.create_all(bind=engine)

# --- 2. 資料接收格式 ---
class ItineraryCreate(BaseModel):
    date: str          
    start_time: str    
    end_time: str      
    location: str      
    notes: Optional[str] = ""     
    map_url: Optional[str] = "" 

class ExpenseCreate(BaseModel):
    item_name: str     
    amount: int        
    payer: str         
    shared_by: List[str]

class MemberCreate(BaseModel):
    name: str

app = FastAPI()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- 3. API 路由 ---

# 【成員管理 API】 
@app.get("/members/")
def get_members(db: Session = Depends(get_db)):
    return db.query(DBMember).all()

@app.post("/members/")
def add_member(member: MemberCreate, db: Session = Depends(get_db)):
    db_member = DBMember(name=member.name)
    db.add(db_member)
    try:
        db.commit()
        return {"status": "success"}
    except:
        db.rollback()
        raise HTTPException(status_code=400, detail="成員名稱已存在")

@app.delete("/members/{member_id}")
def delete_member(member_id: int, db: Session = Depends(get_db)):
    db_member = db.query(DBMember).filter(DBMember.id == member_id).first()
    if db_member:
        db.delete(db_member)
        db.commit()
        return {"status": "success"}
    raise HTTPException(status_code=404)

# 【行程管理 API】 
@app.get("/settings/")
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(DBSetting).all()
    data = {"trip_title": "我的日本之旅", "start_date": "2026-06-30", "end_date": "2026-07-08"}
    for s in settings: data[s.key] = s.value
    return data

@app.post("/settings/")
def update_settings(trip_title: str, start_date: str, end_date: str, db: Session = Depends(get_db)):
    new_data = {"trip_title": trip_title, "start_date": start_date, "end_date": end_date}
    for key, value in new_data.items():
        db_setting = db.query(DBSetting).filter(DBSetting.key == key).first()
        if db_setting: db_setting.value = value
        else: db.add(DBSetting(key=key, value=value))
    db.commit()
    return {"status": "success"}

@app.post("/itinerary/")
def add_itinerary(item: ItineraryCreate, db: Session = Depends(get_db)):
    db_item = DBItinerary(**item.model_dump())
    db.add(db_item)
    db.commit()
    return {"status": "success"}

@app.get("/itinerary/")
def get_itinerary(db: Session = Depends(get_db)):
    return {"data": db.query(DBItinerary).order_by(DBItinerary.date, DBItinerary.start_time).all()}

@app.delete("/itinerary/{item_id}")
def delete_itinerary(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(DBItinerary).filter(DBItinerary.id == item_id).first()
    if db_item:
        db.delete(db_item)
        db.commit()
        return {"status": "success"}
    raise HTTPException(status_code=404)

@app.put("/itinerary/{item_id}")
def update_itinerary(item_id: int, item: ItineraryCreate, db: Session = Depends(get_db)):
    db_item = db.query(DBItinerary).filter(DBItinerary.id == item_id).first()
    if db_item:
        db_item.date, db_item.start_time, db_item.end_time = item.date, item.start_time, item.end_time
        db_item.location, db_item.notes, db_item.map_url = item.location, item.notes, item.map_url
        db.commit()
        return {"status": "success"}
    raise HTTPException(status_code=404)

# 【記帳與結算 API】 
@app.post("/expenses/")
def add_expense(item: ExpenseCreate, db: Session = Depends(get_db)):
    db_item = DBExpense(item_name=item.item_name, amount=item.amount, payer=item.payer, shared_by=json.dumps(item.shared_by))
    db.add(db_item)
    db.commit()
    return {"status": "success"}

@app.get("/expenses/")
def get_expenses(db: Session = Depends(get_db)):
    items = db.query(DBExpense).all()
    return {"data": [{"id": i.id, "item_name": i.item_name, "amount": i.amount, "payer": i.payer, "shared_by": json.loads(i.shared_by)} for i in items]}

@app.get("/settlement/")
def get_settlement(db: Session = Depends(get_db)):
    db_items = db.query(DBExpense).all()
    if not db_items: return {"data": ["目前沒有花費紀錄。"]}
    formatted_expenses = [{"item": i.item_name, "amount": i.amount, "payer": i.payer, "shared_by": json.loads(i.shared_by)} for i in db_items]
    return {"data": minimize_debts(formatted_expenses)}

@app.delete("/expenses/{item_id}")
def delete_expense(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(DBExpense).filter(DBExpense.id == item_id).first()
    if db_item:
        db.delete(db_item)
        db.commit()
        return {"status": "success"}
    raise HTTPException(status_code=404)
