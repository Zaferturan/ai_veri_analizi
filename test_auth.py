"""
🧱 AUTH SYSTEM: Test dosyası

Bu dosya auth.py modülünün testlerini içerir.
"""

import pytest
import tempfile
import os
from auth import AuthSystem, UserRole, User, JWTManager
from datetime import datetime

class TestAuthSystem:
    """AuthSystem sınıfı için testler"""
    
    @pytest.fixture
    def temp_db(self):
        """Geçici veritabanı oluştur"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Test sonrası temizlik
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def auth_system(self, temp_db):
        """Test için AuthSystem instance'ı oluştur"""
        return AuthSystem(temp_db)
    
    def test_init_database(self, auth_system):
        """Veritabanı başlatma testi"""
        # Veritabanı dosyasının oluşturulduğunu kontrol et
        assert os.path.exists(auth_system.db_path)
        
        # Tabloların oluşturulduğunu kontrol et
        import sqlite3
        with sqlite3.connect(auth_system.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            assert cursor.fetchone() is not None
    
    def test_hash_password(self, auth_system):
        """Parola hashleme testi"""
        password = "test123"
        hash1 = auth_system.hash_password(password)
        hash2 = auth_system.hash_password(password)
        
        # Hash'ler farklı olmalı (salt farklı)
        assert hash1 != hash2
        
        # Aynı parola doğrulanabilmeli
        assert auth_system.verify_password(password, hash1)
        assert auth_system.verify_password(password, hash2)
    
    def test_verify_password(self, auth_system):
        """Parola doğrulama testi"""
        password = "test123"
        wrong_password = "wrong123"
        password_hash = auth_system.hash_password(password)
        
        assert auth_system.verify_password(password, password_hash)
        assert not auth_system.verify_password(wrong_password, password_hash)
    
    def test_create_user(self, auth_system):
        """Kullanıcı oluşturma testi"""
        user = auth_system.create_user("testuser", "testpass", UserRole.ADMIN)
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.role == UserRole.ADMIN
        assert user.created_at is not None
        assert auth_system.verify_password("testpass", user.password_hash)
    
    def test_create_duplicate_user(self, auth_system):
        """Aynı kullanıcı adıyla tekrar oluşturma testi"""
        auth_system.create_user("testuser", "testpass", UserRole.ADMIN)
        
        with pytest.raises(ValueError, match="zaten mevcut"):
            auth_system.create_user("testuser", "testpass2", UserRole.ANALYST)
    
    def test_get_user_by_username(self, auth_system):
        """Kullanıcı adına göre kullanıcı getirme testi"""
        # Önce kullanıcı oluştur
        created_user = auth_system.create_user("testuser", "testpass", UserRole.ADMIN)
        
        # Kullanıcıyı getir
        retrieved_user = auth_system.get_user_by_username("testuser")
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.username == "testuser"
        assert retrieved_user.role == UserRole.ADMIN
    
    def test_get_nonexistent_user(self, auth_system):
        """Var olmayan kullanıcı getirme testi"""
        user = auth_system.get_user_by_username("nonexistent")
        assert user is None
    
    def test_authenticate_user(self, auth_system):
        """Kullanıcı doğrulama testi"""
        auth_system.create_user("testuser", "testpass", UserRole.ADMIN)
        
        # Doğru parola ile giriş
        user = auth_system.authenticate_user("testuser", "testpass")
        assert user is not None
        assert user.username == "testuser"
        assert user.role == UserRole.ADMIN
        
        # Yanlış parola ile giriş
        user = auth_system.authenticate_user("testuser", "wrongpass")
        assert user is None
        
        # Var olmayan kullanıcı
        user = auth_system.authenticate_user("nonexistent", "testpass")
        assert user is None
    
    def test_list_users(self, auth_system):
        """Kullanıcı listesi testi"""
        # Başlangıçta boş olmalı
        users = auth_system.list_users()
        assert len(users) == 0
        
        # Kullanıcılar oluştur
        auth_system.create_user("user1", "pass1", UserRole.ADMIN)
        auth_system.create_user("user2", "pass2", UserRole.ANALYST)
        auth_system.create_user("user3", "pass3", UserRole.VIEWER)
        
        users = auth_system.list_users()
        assert len(users) == 3
        
        usernames = [user.username for user in users]
        assert "user1" in usernames
        assert "user2" in usernames
        assert "user3" in usernames
    
    def test_delete_user(self, auth_system):
        """Kullanıcı silme testi"""
        auth_system.create_user("testuser", "testpass", UserRole.ADMIN)
        
        # Kullanıcıyı sil
        success = auth_system.delete_user("testuser")
        assert success
        
        # Kullanıcının silindiğini kontrol et
        user = auth_system.get_user_by_username("testuser")
        assert user is None
        
        # Var olmayan kullanıcıyı silmeye çalış
        success = auth_system.delete_user("nonexistent")
        assert not success

class TestJWTManager:
    """JWTManager sınıfı için testler"""
    
    def test_create_token(self):
        """JWT token oluşturma testi"""
        user = User(
            id=1,
            username="testuser",
            password_hash="hash",
            role=UserRole.ADMIN
        )
        
        token = JWTManager.create_token(user)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token(self):
        """JWT token doğrulama testi"""
        user = User(
            id=1,
            username="testuser",
            password_hash="hash",
            role=UserRole.ADMIN
        )
        
        # Geçerli token oluştur
        token = JWTManager.create_token(user)
        payload = JWTManager.verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"
    
    def test_verify_invalid_token(self):
        """Geçersiz token doğrulama testi"""
        # Geçersiz token
        payload = JWTManager.verify_token("invalid.token.here")
        assert payload is None
        
        # Boş token
        payload = JWTManager.verify_token("")
        assert payload is None

class TestUserRole:
    """UserRole enum testi"""
    
    def test_user_roles(self):
        """Kullanıcı rolleri testi"""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.ANALYST.value == "analyst"
        assert UserRole.VIEWER.value == "viewer"
        
        # Enum değerlerini kontrol et
        roles = [role.value for role in UserRole]
        assert "admin" in roles
        assert "analyst" in roles
        assert "viewer" in roles

class TestUserModel:
    """User Pydantic model testi"""
    
    def test_user_creation(self):
        """User model oluşturma testi"""
        user = User(
            username="testuser",
            password_hash="hash",
            role=UserRole.ADMIN
        )
        
        assert user.username == "testuser"
        assert user.password_hash == "hash"
        assert user.role == UserRole.ADMIN
        assert user.id is None  # Henüz veritabanına kaydedilmemiş
    
    def test_user_validation(self):
        """User model validasyon testi"""
        # Geçerli kullanıcı
        user = User(
            username="testuser",
            password_hash="hash",
            role=UserRole.ADMIN
        )
        assert user.username == "testuser"
        
        # Çok kısa kullanıcı adı (validasyon hatası)
        with pytest.raises(ValueError):
            User(
                username="ab",  # 3 karakterden az
                password_hash="hash",
                role=UserRole.ADMIN
            )

if __name__ == "__main__":
    # Testleri çalıştır
    pytest.main([__file__, "-v"]) 