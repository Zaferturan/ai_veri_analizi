"""
🧱 AUTH SYSTEM: Basit kullanıcı girişi ve rol sistemi

Bu modül kullanıcı doğrulama ve yetkilendirme işlemlerini yönetir.
Desteklenen roller: admin, analyst, viewer
"""

import sqlite3
import bcrypt
import argparse
import json
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime, timedelta
import jwt
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

# JWT Secret Key (production'da environment variable'dan alınmalı)
JWT_SECRET = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 30

# Security scheme for FastAPI
security = HTTPBearer()

class UserRole(str, Enum):
    """Kullanıcı rolleri"""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"

class User(BaseModel):
    """Kullanıcı modeli"""
    id: Optional[int] = None
    username: str = Field(..., min_length=3, max_length=50)
    password_hash: str
    role: UserRole
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

class UserCreate(BaseModel):
    """Kullanıcı oluşturma modeli"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    role: UserRole

class UserLogin(BaseModel):
    """Kullanıcı giriş modeli"""
    username: str
    password: str

class Token(BaseModel):
    """JWT Token modeli"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class AuthSystem:
    """Kullanıcı doğrulama ve yetkilendirme sistemi"""
    
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Veritabanını başlat ve tabloları oluştur"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            conn.commit()
    
    def hash_password(self, password: str) -> str:
        """Parolayı bcrypt ile hashle"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Parola doğrulaması yap"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def create_user(self, username: str, password: str, role: UserRole) -> User:
        """Yeni kullanıcı oluştur"""
        try:
            password_hash = self.hash_password(password)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, password_hash, role)
                    VALUES (?, ?, ?)
                """, (username, password_hash, role.value))
                user_id = cursor.lastrowid
                conn.commit()
                
                return User(
                    id=user_id,
                    username=username,
                    password_hash=password_hash,
                    role=role,
                    created_at=datetime.now()
                )
        except sqlite3.IntegrityError:
            raise ValueError(f"Kullanıcı adı '{username}' zaten mevcut")
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Kullanıcı adına göre kullanıcı getir"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, password_hash, role, created_at, last_login
                FROM users WHERE username = ?
            """, (username,))
            row = cursor.fetchone()
            
            if row:
                return User(
                    id=row[0],
                    username=row[1],
                    password_hash=row[2],
                    role=UserRole(row[3]),
                    created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    last_login=datetime.fromisoformat(row[5]) if row[5] else None
                )
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Kullanıcı doğrulaması yap"""
        user = self.get_user_by_username(username)
        if user and self.verify_password(password, user.password_hash):
            # Son giriş zamanını güncelle
            self.update_last_login(user.id)
            return user
        return None
    
    def update_last_login(self, user_id: int):
        """Kullanıcının son giriş zamanını güncelle"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_id,))
            conn.commit()
    
    def list_users(self) -> list[User]:
        """Tüm kullanıcıları listele"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, password_hash, role, created_at, last_login
                FROM users ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            
            return [
                User(
                    id=row[0],
                    username=row[1],
                    password_hash=row[2],
                    role=UserRole(row[3]),
                    created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    last_login=datetime.fromisoformat(row[5]) if row[5] else None
                )
                for row in rows
            ]
    
    def delete_user(self, username: str) -> bool:
        """Kullanıcı sil"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            return cursor.rowcount > 0

class JWTManager:
    """JWT token yönetimi"""
    
    @staticmethod
    def create_token(user: User) -> str:
        """Kullanıcı için JWT token oluştur"""
        payload = {
            "sub": user.username,
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """JWT token doğrula"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.PyJWTError:
            return None

# Global auth system instance
auth_system = AuthSystem()

# FastAPI app
app = FastAPI(title="Auth System API", version="1.0.0")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Mevcut kullanıcıyı token'dan al"""
    token = credentials.credentials
    payload = JWTManager.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz token"
        )
    
    user = auth_system.get_user_by_username(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı"
        )
    
    return user

def require_role(required_role: UserRole):
    """Belirli bir rol gerektiren decorator"""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu işlem için yetkiniz yok"
            )
        return current_user
    return role_checker

# FastAPI Endpoints
@app.post("/register", response_model=User)
async def register_user(user_data: UserCreate):
    """Yeni kullanıcı kaydı"""
    try:
        user = auth_system.create_user(
            username=user_data.username,
            password=user_data.password,
            role=user_data.role
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/login", response_model=Token)
async def login_user(user_data: UserLogin):
    """Kullanıcı girişi"""
    user = auth_system.authenticate_user(user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kullanıcı adı veya parola"
        )
    
    token = JWTManager.create_token(user)
    return Token(
        access_token=token,
        expires_in=JWT_EXPIRE_MINUTES * 60
    )

@app.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Mevcut kullanıcı bilgilerini getir"""
    return current_user

@app.get("/users", response_model=list[User])
async def list_all_users(current_user: User = Depends(require_role(UserRole.ADMIN))):
    """Tüm kullanıcıları listele (sadece admin)"""
    return auth_system.list_users()

@app.delete("/users/{username}")
async def delete_user(username: str, current_user: User = Depends(require_role(UserRole.ADMIN))):
    """Kullanıcı sil (sadece admin)"""
    if current_user.username == username:
        raise HTTPException(status_code=400, detail="Kendinizi silemezsiniz")
    
    success = auth_system.delete_user(username)
    if not success:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    return {"message": f"Kullanıcı '{username}' silindi"}

# CLI Functions
def cli_register():
    """CLI kullanıcı kaydı"""
    print("=== Kullanıcı Kaydı ===")
    username = input("Kullanıcı adı: ")
    password = input("Parola: ")
    
    print("Roller:")
    for i, role in enumerate(UserRole, 1):
        print(f"{i}. {role.value}")
    
    role_choice = input("Rol seçin (1-3): ")
    role_map = {1: UserRole.ADMIN, 2: UserRole.ANALYST, 3: UserRole.VIEWER}
    
    if role_choice not in ['1', '2', '3']:
        print("Geçersiz rol seçimi!")
        return
    
    try:
        user = auth_system.create_user(username, password, role_map[int(role_choice)])
        print(f"✅ Kullanıcı '{user.username}' başarıyla oluşturuldu!")
    except ValueError as e:
        print(f"❌ Hata: {e}")

def cli_login():
    """CLI kullanıcı girişi"""
    print("=== Kullanıcı Girişi ===")
    username = input("Kullanıcı adı: ")
    password = input("Parola: ")
    
    user = auth_system.authenticate_user(username, password)
    if user:
        print(f"✅ Giriş başarılı! Hoş geldin {user.username} ({user.role.value})")
        return user
    else:
        print("❌ Geçersiz kullanıcı adı veya parola!")
        return None

def cli_list_users():
    """CLI kullanıcı listesi"""
    print("=== Kullanıcı Listesi ===")
    users = auth_system.list_users()
    
    if not users:
        print("Henüz kullanıcı yok.")
        return
    
    print(f"{'ID':<5} {'Kullanıcı Adı':<15} {'Rol':<10} {'Oluşturulma':<20} {'Son Giriş':<20}")
    print("-" * 80)
    
    for user in users:
        created = user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "N/A"
        last_login = user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "Hiç giriş yapmamış"
        print(f"{user.id:<5} {user.username:<15} {user.role.value:<10} {created:<20} {last_login:<20}")

def cli_delete_user():
    """CLI kullanıcı silme"""
    print("=== Kullanıcı Silme ===")
    username = input("Silinecek kullanıcı adı: ")
    
    success = auth_system.delete_user(username)
    if success:
        print(f"✅ Kullanıcı '{username}' silindi!")
    else:
        print(f"❌ Kullanıcı '{username}' bulunamadı!")

def cli_menu():
    """Ana CLI menüsü"""
    while True:
        print("\n" + "="*50)
        print("🧱 AUTH SYSTEM - Ana Menü")
        print("="*50)
        print("1. Kullanıcı Kaydı")
        print("2. Kullanıcı Girişi")
        print("3. Kullanıcı Listesi")
        print("4. Kullanıcı Silme")
        print("5. API Sunucusunu Başlat")
        print("6. Çıkış")
        print("-"*50)
        
        choice = input("Seçiminiz (1-6): ")
        
        if choice == "1":
            cli_register()
        elif choice == "2":
            cli_login()
        elif choice == "3":
            cli_list_users()
        elif choice == "4":
            cli_delete_user()
        elif choice == "5":
            print("🌐 API sunucusu başlatılıyor... http://localhost:8000")
            print("📚 API dokümantasyonu: http://localhost:8000/docs")
            uvicorn.run(app, host="0.0.0.0", port=8000)
        elif choice == "6":
            print("👋 Güle güle!")
            break
        else:
            print("❌ Geçersiz seçim!")

def create_sample_users():
    """Örnek kullanıcılar oluştur"""
    sample_users = [
        ("admin", "admin123", UserRole.ADMIN),
        ("analyst", "analyst123", UserRole.ANALYST),
        ("viewer", "viewer123", UserRole.VIEWER),
    ]
    
    for username, password, role in sample_users:
        try:
            auth_system.create_user(username, password, role)
            print(f"✅ Örnek kullanıcı oluşturuldu: {username} ({role.value})")
        except ValueError:
            print(f"⚠️  Kullanıcı zaten mevcut: {username}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auth System CLI")
    parser.add_argument("--api", action="store_true", help="API sunucusunu başlat")
    parser.add_argument("--create-samples", action="store_true", help="Örnek kullanıcılar oluştur")
    parser.add_argument("--cli", action="store_true", help="CLI menüsünü başlat")
    
    args = parser.parse_args()
    
    if args.create_samples:
        create_sample_users()
    elif args.api:
        print("🌐 API sunucusu başlatılıyor... http://localhost:8000")
        print("📚 API dokümantasyonu: http://localhost:8000/docs")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        cli_menu() 