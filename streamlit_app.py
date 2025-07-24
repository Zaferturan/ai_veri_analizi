"""
Streamlit Web Arayüzü - VeriKeşif Platformu

Bu modül, kullanıcıların veritabanı analizi ve AI fonksiyonlarını
kolayca kullanabilecekleri bir web arayüzü sağlar.

Özellikler:
- MySQL veritabanı bağlantısı
- Tablo seçimi ve önizleme
- AI analizleri (özetleme, sınıflandırma, kümelendirme)
- Embedding cache durumu
- Metrik izleme
- Veri yükleme arayüzü (.csv, .xlsx, .sql dosyaları)
"""

import streamlit as st
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine, text
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import time
import json
import logging
from datetime import datetime, timedelta
import sqlite3
import bcrypt
import jwt
from typing import List, Dict, Any, Optional
import io
import tempfile
import re

# .env dosyasını yükle
load_dotenv('.env')

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Auth constants
JWT_SECRET = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"

# Module availability check
try:
    from explorer import DataExplorer
    from ai_helper import AIHelper
    from embedding_cache import EmbeddingCache
    from metrics import get_metrics_summary, MetricsCollector
    EXPLORER_AVAILABLE = True
    AI_HELPER_AVAILABLE = True
    CACHE_AVAILABLE = True
    METRICS_AVAILABLE = True
except ImportError as e:
    st.error(f"Modül import hatası: {e}")
    EXPLORER_AVAILABLE = False
    AI_HELPER_AVAILABLE = False
    CACHE_AVAILABLE = False
    METRICS_AVAILABLE = False

# Sayfa konfigürasyonu
st.set_page_config(
    page_title="VeriKeşif - AI Destekli Talep Analizi",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

class AuthSystem:
    """Basit auth sistemi - Streamlit için"""
    
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Veritabanını başlat"""
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
            # Varsayılan admin kullanıcısı oluştur
            self.create_default_admin()
    
    def create_default_admin(self):
        """Varsayılan admin kullanıcısı oluştur"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
                if cursor.fetchone()[0] == 0:
                    password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    cursor.execute("""
                        INSERT INTO users (username, password_hash, role)
                        VALUES (?, ?, ?)
                    """, ("admin", password_hash, "admin"))
                    conn.commit()
                    logger.info("Varsayılan admin kullanıcısı oluşturuldu: admin/admin123")
        except Exception as e:
            logger.error(f"Varsayılan admin oluşturma hatası: {e}")
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Parola doğrulaması"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Kullanıcı doğrulama"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()
                
                if user and self.verify_password(password, user[2]):
                    # Son giriş zamanını güncelle
                    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user[0],))
                    conn.commit()
                    
                    return {
                        'id': user[0],
                        'username': user[1],
                        'role': user[3],
                        'created_at': user[4],
                        'last_login': user[5]
                    }
        except Exception as e:
            logger.error(f"Kullanıcı doğrulama hatası: {e}")
        return None
    
    def create_token(self, user: dict) -> str:
        """JWT token oluştur"""
        payload = {
            'user_id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[dict]:
        """JWT token doğrula"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

class StreamlitApp:
    """Streamlit uygulaması ana sınıfı"""
    
    def __init__(self):
        self.auth_system = AuthSystem()
        self.engine = None
        self.explorer = None
        self.ai_helper = None
        self.cache = None
        self.connection_status = False
        
    def load_csv_file(self, uploaded_file, separator=',') -> pd.DataFrame:
        """CSV dosyasını yükle"""
        try:
            # Encoding tespiti
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            df = None
            
            for encoding in encodings:
                try:
                    uploaded_file.seek(0)  # Dosya pointer'ını başa al
                    df = pd.read_csv(uploaded_file, encoding=encoding, sep=separator)
                    break
                except UnicodeDecodeError:
                    continue
                    
            if df is None:
                raise ValueError("Dosya encoding'i tespit edilemedi")
                
            return df
        except Exception as e:
            raise Exception(f"CSV dosyası yüklenirken hata: {e}")
    
    def detect_csv_separator(self, uploaded_file) -> str:
        """CSV dosyasının ayırıcısını otomatik tespit et"""
        try:
            uploaded_file.seek(0)
            sample = uploaded_file.read(1024).decode('utf-8', errors='ignore')
            uploaded_file.seek(0)
            
            # Yaygın ayırıcıları test et
            separators = [',', ';', '\t', '|']
            max_fields = 0
            best_separator = ','
            
            for sep in separators:
                try:
                    lines = sample.split('\n')[:5]  # İlk 5 satırı kontrol et
                    field_counts = []
                    
                    for line in lines:
                        if line.strip():
                            fields = line.split(sep)
                            field_counts.append(len(fields))
                    
                    if field_counts:
                        avg_fields = sum(field_counts) / len(field_counts)
                        if avg_fields > max_fields:
                            max_fields = avg_fields
                            best_separator = sep
                            
                except:
                    continue
            
            return best_separator
        except:
            return ','  # Varsayılan olarak virgül
    
    def load_excel_file(self, uploaded_file) -> pd.DataFrame:
        """Excel dosyasını yükle"""
        try:
            # Excel dosyasını oku
            df = pd.read_excel(uploaded_file, engine='openpyxl')
            return df
        except Exception as e:
            raise Exception(f"Excel dosyası yüklenirken hata: {e}")
    
    def execute_sql_file(self, uploaded_file, engine) -> str:
        """SQL dosyasını çalıştır"""
        try:
            # SQL dosyasını oku
            sql_content = uploaded_file.read().decode('utf-8')
            
            # SQL komutlarını ayır (; ile ayrılmış)
            sql_commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip()]
            
            results = []
            with engine.connect() as conn:
                for i, command in enumerate(sql_commands):
                    if command:
                        try:
                            result = conn.execute(text(command))
                            if result.returns_rows:
                                # SELECT komutu ise sonuçları al
                                rows = result.fetchall()
                                results.append(f"Komut {i+1}: {len(rows)} satır döndürüldü")
                            else:
                                # INSERT, UPDATE, DELETE gibi komutlar
                                results.append(f"Komut {i+1}: Başarıyla çalıştırıldı")
                            conn.commit()
                        except Exception as e:
                            results.append(f"Komut {i+1} hatası: {e}")
                            
            return "\n".join(results)
        except Exception as e:
            raise Exception(f"SQL dosyası çalıştırılırken hata: {e}")
    
    def save_dataframe_to_database(self, df: pd.DataFrame, table_name: str, engine, if_exists: str = 'replace') -> bool:
        """DataFrame'i veritabanına kaydet"""
        try:
            # Tablo adını temizle (sadece alfanumerik ve alt çizgi)
            clean_table_name = re.sub(r'[^a-zA-Z0-9_]', '_', table_name)
            
            # DataFrame'i veritabanına yaz
            df.to_sql(
                name=clean_table_name,
                con=engine,
                if_exists=if_exists,
                index=False,
                method='multi',
                chunksize=1000
            )
            
            return True
        except Exception as e:
            raise Exception(f"Veritabanına kaydetme hatası: {e}")
    
    def get_database_list(self, engine) -> List[str]:
        """Mevcut veritabanlarını listele"""
        try:
            # MySQL için veritabanı listesi
            if 'mysql' in str(engine.url):
                with engine.connect() as conn:
                    result = conn.execute(text("SHOW DATABASES"))
                    databases = [row[0] for row in result.fetchall() 
                               if row[0] not in ['information_schema', 'mysql', 'performance_schema', 'sys']]
                return databases
            else:
                # SQLite için sadece mevcut veritabanı
                return [engine.url.database or 'main']
        except Exception as e:
            logger.error(f"Veritabanı listesi alınırken hata: {e}")
            return []
    
    def get_table_list(self, engine, database_name: str = None) -> List[str]:
        """Belirtilen veritabanındaki tabloları listele"""
        try:
            with engine.connect() as conn:
                if database_name and 'mysql' in str(engine.url):
                    # Belirli bir veritabanındaki tabloları listele
                    conn.execute(text(f"USE `{database_name}`"))
                    result = conn.execute(text("SHOW TABLES"))
                    tables = [row[0] for row in result.fetchall()]
                else:
                    # Mevcut veritabanındaki tabloları listele
                    result = conn.execute(text("SHOW TABLES"))
                    tables = [row[0] for row in result.fetchall()]
                return tables
        except Exception as e:
            logger.error(f"Tablo listesi alınırken hata: {e}")
            return []
    
    def create_database(self, database_name: str, engine) -> bool:
        """Yeni veritabanı oluştur"""
        try:
            # MySQL için yeni veritabanı oluştur
            if 'mysql' in str(engine.url):
                # Ana MySQL sunucusuna bağlan
                mysql_host = os.getenv('MYSQL_HOST', 'localhost')
                mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
                mysql_user = os.getenv('MYSQL_USER', 'root')
                mysql_password = os.getenv('MYSQL_PASSWORD', '')
                
                temp_connection_string = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}"
                temp_engine = create_engine(temp_connection_string)
                
                with temp_engine.connect() as conn:
                    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database_name}`"))
                    conn.commit()
                    
                return True
            else:
                # SQLite için veritabanı zaten mevcut
                return True
        except Exception as e:
            raise Exception(f"Veritabanı oluşturma hatası: {e}")
        
    def init_session_state(self):
        """Session state'i başlat"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'token' not in st.session_state:
            st.session_state.token = None
        if 'engine' not in st.session_state:
            st.session_state.engine = None
        if 'connection_established' not in st.session_state:
            st.session_state.connection_established = False
        if 'selected_table' not in st.session_state:
            st.session_state.selected_table = None
        if 'table_data' not in st.session_state:
            st.session_state.table_data = None
        if 'analysis_results' not in st.session_state:
            st.session_state.analysis_results = None
        if 'show_ai_analysis' not in st.session_state:
            st.session_state.show_ai_analysis = False
        if 'ai_model' not in st.session_state:
            st.session_state.ai_model = "llama3:latest"
        if 'ai_action' not in st.session_state:
            st.session_state.ai_action = "Özetleme"
        if 'custom_prompt' not in st.session_state:
            st.session_state.custom_prompt = None
        if 'custom_system_prompt' not in st.session_state:
            st.session_state.custom_system_prompt = None
        if 'custom_defaults' not in st.session_state:
            st.session_state.custom_defaults = {}
        if 'custom_system_defaults' not in st.session_state:
            st.session_state.custom_system_defaults = {}
        if 'available_models' not in st.session_state:
            st.session_state.available_models = ["llama3:latest", "qwen2.5-coder:32b-instruct-q4_0", "mistral:latest"]
        if 'uploaded_data' not in st.session_state:
            st.session_state.uploaded_data = None
        if 'uploaded_table_name' not in st.session_state:
            st.session_state.uploaded_table_name = None
        if 'show_data_upload' not in st.session_state:
            st.session_state.show_data_upload = False
        
    def render_auth_section(self):
        """Auth bölümünü göster - GELİŞTİRME SÜRECİNDE DEVRE DIŞI"""
        # Geliştirme sürecinde auth sistemi devre dışı
        st.session_state.authenticated = True
        st.session_state.user = {'username': 'admin', 'role': 'admin'}
        
        # Uyarıları gösterme - sessizce devre dışı bırak
    
    def render_header(self):
        """Ana başlığı göster"""
        # Sidebar toggle'ı görünür yapmak için CSS
        st.markdown("""
        <style>
        /* Sidebar toggle butonunu görünür yap - BASİT VE ETKİLİ */
        [data-testid="collapsedControl"] {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            position: fixed !important;
            top: 10px !important;
            left: 10px !important;
            z-index: 9999 !important;
            background-color: #1f77b4 !important;
            color: white !important;
            border-radius: 50% !important;
            width: 40px !important;
            height: 40px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
            font-size: 16px !important;
            cursor: pointer !important;
        }
        
        /* Sidebar toggle butonuna hover efekti */
        [data-testid="collapsedControl"]:hover {
            background-color: #1565c0 !important;
            transform: scale(1.1) !important;
        }
        
        /* Sidebar kapalıyken toggle butonunu göster */
        .stApp[data-collapsed="true"] [data-testid="collapsedControl"] {
            display: block !important;
            visibility: visible !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Logo ve başlık yan yana
        col1, col2 = st.columns([1, 4])
        
        with col1:
            try:
                st.image("logo.png", width=80)
            except:
                st.markdown("🔍")  # Logo yoksa emoji göster
                
        with col2:
            st.markdown('<h1 class="main-header">🔍 Nilüfer Kaşif - AI Destekli Veri Analizi</h1>', 
                       unsafe_allow_html=True)
        
        st.markdown("---")
        
    def render_sidebar(self):
        """Sidebar'ı oluştur"""
        with st.sidebar:
            # Auth bölümü
            self.render_auth_section()
            
            # Sadece giriş yapmış kullanıcılar için diğer bölümler
            if st.session_state.authenticated:
                st.markdown("---")
                
                # Veri yükleme bölümü
                st.subheader("📁 Veri Yükle")
                
                # Veri yükleme toggle butonu
                if st.button("📁 Veri Yükle", key="data_upload_toggle"):
                    st.session_state.show_data_upload = not st.session_state.show_data_upload
                
                # Veri yükleme arayüzü
                if st.session_state.get('show_data_upload', False):
                    self._render_data_upload_section()
                
                st.markdown("---")
                
                # Veritabanı bağlantısı
                st.subheader("📊 Veritabanı Bağlantısı")
                
                # Veritabanı seçimi
                database = st.selectbox(
                    "Veritabanı Seçin",
                    ["belediye_kayitlari", "test_db", "production_db"],
                    help="Bağlanmak istediğiniz veritabanını seçin"
                )
                
                # Bağlan butonu
                if st.button("🔗 Bağlan", type="primary"):
                    try:
                        # MySQL bağlantısı
                        mysql_host = os.getenv('MYSQL_HOST', 'localhost')
                        mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
                        mysql_user = os.getenv('MYSQL_USER', 'root')
                        mysql_password = os.getenv('MYSQL_PASSWORD', '')
                        
                        connection_string = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{database}"
                        self.engine = create_engine(connection_string)
                        
                        # Bağlantıyı test et
                        with self.engine.connect() as conn:
                            conn.execute(text("SELECT 1"))
                            
                        st.session_state.connection_established = True
                        st.session_state.engine = self.engine
                        self.connection_status = True
                        st.success(f"✅ {database} veritabanına başarıyla bağlandı!")
                        
                        # Explorer'ı başlat
                        if EXPLORER_AVAILABLE:
                            self.explorer = DataExplorer(self.engine)
                            
                    except Exception as e:
                        st.error(f"❌ Bağlantı hatası: {e}")
                        st.session_state.connection_established = False
                        self.connection_status = False
                    
                # AI ayarları - sadece veritabanı bağlantısı kurulduğunda göster
                if st.session_state.get('connection_established', False):
                    st.subheader("🤖 AI Ayarları")
                    
                    # AI modeli seçimi - Dinamik olarak güncelle
                    try:
                        ai_helper = AIHelper()
                        available_models = ai_helper.get_available_models()
                        st.session_state.available_models = available_models
                    except:
                        if 'available_models' not in st.session_state:
                            st.session_state.available_models = ["llama3:latest", "qwen2.5-coder:32b-instruct-q4_0", "mistral:latest"]
                    
                    ai_model = st.selectbox(
                        "AI Modeli",
                        st.session_state.available_models,
                        help="Kullanmak istediğiniz Ollama modelini seçin",
                        key="ai_model_select"
                    )
                    
                    # AI işlemi seçimi
                    ai_action = st.selectbox(
                        "AI İşlemi",
                        ["Özetleme", "Sınıflandırma", "Kümelendirme", "Trend Analizi"],
                        help="Yapmak istediğiniz AI analizini seçin",
                        key="ai_action_select"
                    )
                    
                    # Otomatik kaydet
                    if ai_model != st.session_state.get('ai_model') or ai_action != st.session_state.get('ai_action'):
                        st.session_state.ai_model = ai_model
                        st.session_state.ai_action = ai_action
                        st.success("✅ AI ayarları otomatik kaydedildi!")
                    
                    # Modelleri güncelle butonu
                    if st.button("🔄 Modelleri Güncelle"):
                        try:
                            ai_helper = AIHelper()
                            new_models = ai_helper.get_available_models()
                            st.session_state.available_models = new_models
                            st.success(f"✅ {len(new_models)} model güncellendi!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Model güncelleme hatası: {e}")
                    
                    # Cache durumu
                    st.subheader("💾 Cache Durumu")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📊 Cache Durumunu Göster"):
                            try:
                                cache = EmbeddingCache()
                                stats = cache.get_cache_stats()
                                st.json(stats)
                            except Exception as e:
                                st.error(f"Cache durumu alınamadı: {e}")
                    
                    with col2:
                        if st.button("🗑️ Cache Temizle"):
                            try:
                                cache = EmbeddingCache()
                                cache.clear_cache()
                                st.success("✅ Cache temizlendi!")
                            except Exception as e:
                                st.error(f"Cache temizleme hatası: {e}")
                    
                    # Metrikler
                    st.subheader("📈 Metrikler")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("📊 Metrikleri Göster"):
                            try:
                                metrics = MetricsCollector()
                                stats = metrics.get_metrics_summary()
                                
                                # Ana metrikler
                                st.metric("📞 Toplam AI Çağrısı", stats['stats']['total_calls'])
                                st.metric("🔤 Toplam Token", stats['stats']['total_tokens'])
                                st.metric("❌ Toplam Hata", stats['stats']['total_errors'])
                                
                                # Model bazlı istatistikler
                                if stats['stats']['model_stats']:
                                    st.subheader("🤖 Model İstatistikleri")
                                    for model, model_stats in stats['stats']['model_stats'].items():
                                        with st.expander(f"📊 {model}"):
                                            col1, col2, col3 = st.columns(3)
                                            with col1:
                                                st.metric("Çağrı", model_stats.get('calls', 0))
                                            with col2:
                                                st.metric("Token", model_stats.get('tokens', 0))
                                            with col3:
                                                st.metric("Hata", model_stats.get('errors', 0))
                                
                                # Son çağrı zamanı
                                if stats['stats']['last_call_time']:
                                    st.info(f"🕐 Son çağrı: {stats['stats']['last_call_time']}")
                                    
                            except Exception as e:
                                st.error(f"Metrikler alınamadı: {e}")
                    
                    with col2:
                        if st.button("🔄 Metrikleri Sıfırla"):
                            try:
                                metrics = MetricsCollector()
                                metrics.reset_metrics()
                                st.success("✅ Metrikler sıfırlandı!")
                            except Exception as e:
                                st.error(f"Metrik sıfırlama hatası: {e}")
                    
                    with col3:
                        if st.button("📤 Metrikleri Dışa Aktar"):
                            try:
                                metrics = MetricsCollector()
                                export_data = metrics.export_metrics()
                                
                                # JSON dosyası olarak indir
                                st.download_button(
                                    label="📥 JSON İndir",
                                    data=export_data,
                                    file_name=f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                    mime="application/json"
                                )
                                st.success("✅ Metrikler dışa aktarıldı!")
                            except Exception as e:
                                st.error(f"Metrik dışa aktarma hatası: {e}")
                
                # Deploy butonu - sidebar'ın en altına
                st.markdown("---")
                st.markdown("### 🚀 Deployment")
                if st.button("📤 Deploy Et", help="Uygulamayı production'a deploy et"):
                    st.info("🚀 Deploy işlemi başlatılıyor...")
                    st.info("💡 Production deployment için `./deploy.sh` komutunu kullanın.")
            else:
                # Giriş yapmamış kullanıcılar için bilgi
                st.info("🔐 Giriş yaparak tüm özelliklere erişebilirsiniz.")
                
                # Demo bilgileri
                st.markdown("---")
                st.markdown("### 🎯 Demo Bilgileri")
                st.markdown("""
                **Varsayılan Kullanıcı:**
                - Kullanıcı Adı: `admin`
                - Şifre: `admin123`
                - Rol: `admin`
                """)
                
                # Deploy butonu - sidebar'ın en altına
                st.markdown("---")
                st.markdown("### 🚀 Deployment")
                if st.button("📤 Deploy Et", help="Uygulamayı production'a deploy et"):
                    st.info("🚀 Deploy işlemi başlatılıyor...")
                    st.info("💡 Production deployment için `./deploy.sh` komutunu kullanın.")

    def _render_mysql_connection(self):
        """MySQL bağlantı formu"""
        # .env'den veritabanı bilgilerini al
        mysql_host = os.getenv('MYSQL_HOST', 'localhost')
        mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
        mysql_user = os.getenv('MYSQL_USER', 'root')
        mysql_password = os.getenv('MYSQL_PASSWORD', '')
        
        with st.form("mysql_connection"):
            st.info(f"🔗 MySQL Bağlantısı: {mysql_host}:{mysql_port}")
            st.info(f"👤 Kullanıcı: {mysql_user}")
            
            # Önce veritabanı listesini çek
            try:
                # MySQL sunucusuna bağlan (veritabanı belirtmeden)
                temp_connection_string = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}"
                temp_engine = create_engine(temp_connection_string)
                
                with temp_engine.connect() as conn:
                    result = conn.execute(text("SHOW DATABASES"))
                    databases = [row[0] for row in result.fetchall() if row[0] not in ['information_schema', 'mysql', 'performance_schema', 'sys']]
                
                if not databases:
                    st.error("❌ Kullanıcının erişebileceği veritabanı bulunamadı!")
                    return
                    
            except Exception as e:
                st.error(f"❌ MySQL sunucusuna bağlanılamadı: {e}")
                return
            
            # Veritabanı seçimi
            database = st.selectbox(
                "Veritabanı Seçin",
                options=databases,
                help="Bağlanılacak veritabanını seçin"
            )
            
            submitted = st.form_submit_button("Bağlan")
            
            if submitted:
                if not database:
                    st.error("Lütfen bir veritabanı seçin!")
                    return
                    
                try:
                    connection_string = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{database}"
                    self.engine = create_engine(connection_string)
                    
                    # Bağlantıyı test et
                    with self.engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                        
                    st.session_state.connection_established = True
                    st.session_state.engine = self.engine  # Engine'i session state'e kaydet
                    self.connection_status = True
                    st.success(f"✅ {database} veritabanına başarıyla bağlandı!")
                    
                    # Explorer'ı başlat
                    if EXPLORER_AVAILABLE:
                        self.explorer = DataExplorer(self.engine)
                        
                except Exception as e:
                    st.error(f"❌ Bağlantı hatası: {e}")
                    st.session_state.connection_established = False
                    self.connection_status = False
                    
    def _render_sqlite_connection(self):
        """SQLite bağlantı formu"""
        # .env'den SQLite veritabanı listesini al
        sqlite_databases = os.getenv('SQLITE_DATABASES', 'users.db,embedding_cache.db').split(',')
        
        with st.form("sqlite_connection"):
            st.info("💾 SQLite Veritabanı Bağlantısı")
            
            # Veritabanı seçimi
            db_path = st.selectbox(
                "Veritabanı Dosyası Seçin",
                options=sqlite_databases,
                help="Bağlanılacak SQLite veritabanı dosyasını seçin"
            )
            
            submitted = st.form_submit_button("Bağlan")
            
            if submitted:
                if not db_path:
                    st.error("Lütfen bir veritabanı dosyası seçin!")
                    return
                    
                try:
                    self.engine = create_engine(f"sqlite:///{db_path}")
                    
                    # Bağlantıyı test et
                    with self.engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                        
                    st.session_state.connection_established = True
                    st.session_state.engine = self.engine  # Engine'i session state'e kaydet
                    self.connection_status = True
                    st.success(f"✅ {db_path} veritabanına başarıyla bağlandı!")
                    
                    # Explorer'ı başlat
                    if EXPLORER_AVAILABLE:
                        self.explorer = DataExplorer(self.engine)
                        
                except Exception as e:
                    st.error(f"❌ Bağlantı hatası: {e}")
                    st.session_state.connection_established = False
                    self.connection_status = False
                    
    def _render_data_upload_section(self):
        """Veri yükleme arayüzü"""
        st.markdown("---")
        
        # Dosya yükleme
        uploaded_file = st.file_uploader(
            "📁 Dosya Seçin",
            type=['csv', 'xlsx', 'sql'],
            help="CSV, Excel veya SQL dosyası yükleyin (Max: 200 MB)"
        )
        
        if uploaded_file is not None:
            # Dosya boyutu kontrolü (200 MB)
            if uploaded_file.size > 200 * 1024 * 1024:
                st.error("❌ Dosya boyutu 200 MB'dan büyük olamaz!")
                return
            
            # Dosya türü kontrolü
            file_extension = uploaded_file.name.split('.')[-1].lower()
            
            if file_extension not in ['csv', 'xlsx', 'sql']:
                st.error("❌ Desteklenmeyen dosya türü!")
                return
            
            # Dosya bilgilerini göster
            st.info(f"📄 Dosya: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
            
            # Veritabanı seçimi
            st.subheader("🗄️ Veritabanı Seçimi")
            
            # Mevcut veritabanları
            existing_databases = []
            
            # .env dosyasındaki MySQL bilgileriyle otomatik bağlantı kur
            try:
                mysql_host = os.getenv('MYSQL_HOST', 'localhost')
                mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
                mysql_user = os.getenv('MYSQL_USER', 'root')
                mysql_password = os.getenv('MYSQL_PASSWORD', '')
                
                # Ana MySQL sunucusuna bağlan
                temp_connection_string = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}"
                temp_engine = create_engine(temp_connection_string)
                
                # Veritabanı listesini al
                existing_databases = self.get_database_list(temp_engine)
                
                # Session state'i güncelle
                if not st.session_state.get('connection_established', False):
                    st.session_state.engine = temp_engine
                    st.session_state.connection_established = True
                    
            except Exception as e:
                st.error(f"❌ MySQL bağlantısı kurulamadı: {e}")
                st.info("💡 Lütfen .env dosyasındaki MySQL bağlantı bilgilerini kontrol edin")
                return
            
            # Veritabanı seçenekleri
            db_options = ["Yeni veritabanı oluştur"] + existing_databases
            
            selected_db_option = st.selectbox(
                "Veritabanı seçin:",
                options=db_options,
                help="Mevcut bir veritabanı seçin veya yeni bir veritabanı oluşturun"
            )
            
            # Yeni veritabanı adı (eğer seçildiyse)
            new_database_name = None
            target_database = None
            
            if selected_db_option == "Yeni veritabanı oluştur":
                new_database_name = st.text_input(
                    "Yeni veritabanı adı:",
                    help="Yeni veritabanı için bir isim girin"
                )
                if not new_database_name:
                    st.warning("⚠️ Lütfen yeni veritabanı adı girin!")
                    return
                target_database = new_database_name
            else:
                target_database = selected_db_option
            
            # Tablo seçimi
            st.subheader("📋 Tablo Seçimi")
            
            # Mevcut tablolar (eğer veritabanı seçildiyse)
            existing_tables = []
            if target_database and target_database != "Yeni veritabanı oluştur":
                try:
                    engine = st.session_state.get('engine')
                    if engine:
                        existing_tables = self.get_table_list(engine, target_database)
                except:
                    pass
            
            # Tablo seçenekleri
            table_options = ["Yeni tablo oluştur"] + existing_tables
            
            selected_table_option = st.selectbox(
                "Tablo seçin:",
                options=table_options,
                help="Mevcut bir tablo seçin veya yeni bir tablo oluşturun"
            )
            
            # Tablo adı
            if selected_table_option == "Yeni tablo oluştur":
                default_table_name = uploaded_file.name.split('.')[0].lower()
                table_name = st.text_input(
                    "Yeni tablo adı:",
                    value=default_table_name,
                    help="Veritabanında oluşturulacak tablonun adı"
                )
                
                if not table_name:
                    st.warning("⚠️ Lütfen tablo adı girin!")
                    return
            else:
                table_name = selected_table_option
                st.info(f"📋 Seçilen tablo: {table_name}")
            
            # Mevcut tablo bilgisi
            if selected_table_option != "Yeni tablo oluştur" and existing_tables:
                st.warning(f"⚠️ '{table_name}' tablosu zaten mevcut. Yükleme seçeneklerini dikkatli seçin!")
            
            # Yükleme seçenekleri
            st.subheader("⚙️ Yükleme Seçenekleri")
            
            col1, col2 = st.columns(2)
            with col1:
                if selected_table_option == "Yeni tablo oluştur":
                    if_exists = 'replace'  # Yeni tablo için her zaman replace
                    st.info("🆕 Yeni tablo oluşturulacak")
                else:
                    if_exists = st.selectbox(
                        "Mevcut tablo için:",
                        options=[
                            ('replace', 'Tabloyu sil ve yeniden oluştur'),
                            ('append', 'Mevcut verilere ekle'),
                            ('fail', 'Hata ver (işlemi durdur)')
                        ],
                        format_func=lambda x: x[1],
                        help="Mevcut tablo varsa ne yapılacağını seçin"
                    )
                    if_exists = if_exists[0]  # Tuple'dan ilk değeri al
            
            with col2:
                # CSV için ek seçenekler
                if file_extension == 'csv':
                    # Otomatik ayırıcı tespiti
                    detected_separator = self.detect_csv_separator(uploaded_file)
                    
                    separator = st.selectbox(
                        "Ayırıcı:",
                        options=[',', ';', '\t', '|'],
                        index=[',', ';', '\t', '|'].index(detected_separator) if detected_separator in [',', ';', '\t', '|'] else 0,
                        help=f"CSV dosyasındaki alan ayırıcısı (Otomatik tespit: {detected_separator})"
                    )
            
            # Yükle butonu
            if st.button("🚀 Yükle", type="primary"):
                try:
                    with st.spinner("Dosya yükleniyor..."):
                        # 1. Veritabanı bağlantısı
                        if new_database_name:
                            # Yeni veritabanı oluştur
                            mysql_host = os.getenv('MYSQL_HOST', 'localhost')
                            mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
                            mysql_user = os.getenv('MYSQL_USER', 'root')
                            mysql_password = os.getenv('MYSQL_PASSWORD', '')
                            
                            # Ana MySQL sunucusuna bağlan
                            temp_connection_string = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}"
                            temp_engine = create_engine(temp_connection_string)
                            
                            # Yeni veritabanı oluştur
                            self.create_database(new_database_name, temp_engine)
                            
                            # Yeni veritabanına bağlan
                            target_connection_string = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{new_database_name}"
                            target_engine = create_engine(target_connection_string)
                            
                            # Session state'i güncelle
                            st.session_state.engine = target_engine
                            st.session_state.connection_established = True
                            target_database = new_database_name
                            
                        else:
                            # Mevcut veritabanını kullan
                            mysql_host = os.getenv('MYSQL_HOST', 'localhost')
                            mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
                            mysql_user = os.getenv('MYSQL_USER', 'root')
                            mysql_password = os.getenv('MYSQL_PASSWORD', '')
                            
                            # Seçilen veritabanına bağlan
                            target_connection_string = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{target_database}"
                            target_engine = create_engine(target_connection_string)
                            
                            # Session state'i güncelle
                            st.session_state.engine = target_engine
                            st.session_state.connection_established = True
                        
                        # 2. Dosyayı işle
                        if file_extension == 'csv':
                            # CSV dosyasını yükle
                            df = self.load_csv_file(uploaded_file, separator)
                            
                            # Veritabanına kaydet
                            success = self.save_dataframe_to_database(df, table_name, target_engine, if_exists)
                            
                            if success:
                                st.success(f"✅ CSV dosyası başarıyla yüklendi!")
                                st.info(f"📊 {len(df)} satır, {len(df.columns)} kolon")
                                
                                # Veri önizleme
                                st.subheader("👀 Veri Önizleme")
                                st.dataframe(df.head(10))
                                
                                # Session state'i güncelle
                                st.session_state.uploaded_data = df
                                st.session_state.uploaded_table_name = table_name
                                st.session_state.selected_table = table_name
                                
                        elif file_extension == 'xlsx':
                            # Excel dosyasını yükle
                            df = self.load_excel_file(uploaded_file)
                            
                            # Veritabanına kaydet
                            success = self.save_dataframe_to_database(df, table_name, target_engine, if_exists)
                            
                            if success:
                                st.success(f"✅ Excel dosyası başarıyla yüklendi!")
                                st.info(f"📊 {len(df)} satır, {len(df.columns)} kolon")
                                
                                # Veri önizleme
                                st.subheader("👀 Veri Önizleme")
                                st.dataframe(df.head(10))
                                
                                # Session state'i güncelle
                                st.session_state.uploaded_data = df
                                st.session_state.uploaded_table_name = table_name
                                st.session_state.selected_table = table_name
                                
                        elif file_extension == 'sql':
                            # SQL dosyasını çalıştır
                            result = self.execute_sql_file(uploaded_file, target_engine)
                            
                            st.success(f"✅ SQL dosyası başarıyla çalıştırıldı!")
                            st.info("📋 Çalıştırılan komutlar:")
                            st.text(result)
                            
                            # SQL dosyası için tablo seçimi
                            st.info("💡 SQL dosyası çalıştırıldı. Analiz etmek istediğiniz tabloyu seçin.")
                            
                        # Başarı mesajı
                        st.success(f"🎉 Veri yükleme tamamlandı!")
                        st.info(f"📁 Veritabanı: {target_database}")
                        st.info(f"📋 Tablo: {table_name}")
                        
                        # Analize başla butonu
                        if file_extension in ['csv', 'xlsx']:
                            if st.button("🔍 Analize Başla", type="primary"):
                                st.session_state.show_data_upload = False
                                st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Yükleme hatası: {e}")
                    logger.error(f"Veri yükleme hatası: {e}")
    
    def _render_postgresql_connection(self):
        """PostgreSQL bağlantı formu"""
        # .env'den PostgreSQL veritabanı bilgilerini al
        postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
        postgres_port = int(os.getenv('POSTGRES_PORT', '5432'))
        postgres_user = os.getenv('POSTGRES_USER', 'postgres')
        postgres_password = os.getenv('POSTGRES_PASSWORD', '')
        postgres_databases = os.getenv('POSTGRES_DATABASES', 'analiz_db').split(',')
        
        with st.form("postgresql_connection"):
            st.info(f"🐘 PostgreSQL Bağlantısı: {postgres_host}:{postgres_port}")
            st.info(f"👤 Kullanıcı: {postgres_user}")
            
            # Veritabanı seçimi
            database = st.selectbox(
                "Veritabanı Seçin",
                options=postgres_databases,
                help="Bağlanılacak PostgreSQL veritabanını seçin"
            )
            
            submitted = st.form_submit_button("Bağlan")
            
            if submitted:
                if not database:
                    st.error("Lütfen bir veritabanı seçin!")
                    return
                    
                try:
                    connection_string = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{database}"
                    self.engine = create_engine(connection_string)
                    
                    # Bağlantıyı test et
                    with self.engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                        
                    st.session_state.connection_established = True
                    self.connection_status = True
                    st.success(f"✅ {database} veritabanına başarıyla bağlandı!")
                    
                    # Explorer'ı başlat
                    if EXPLORER_AVAILABLE:
                        self.explorer = DataExplorer(self.engine)
                        
                except Exception as e:
                    st.error(f"❌ Bağlantı hatası: {e}")
                    st.session_state.connection_established = False
                    self.connection_status = False
                    
    def render_main_content(self):
        """Ana içeriği göster"""
        # Geliştirme sürecinde auth kontrolü yok
        
        # Yüklenen veri varsa göster
        if st.session_state.get('uploaded_data') is not None:
            st.subheader("📁 Yüklenen Veri")
            
            uploaded_df = st.session_state.uploaded_data
            uploaded_table = st.session_state.uploaded_table_name
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Satır Sayısı", len(uploaded_df))
            with col2:
                st.metric("📋 Kolon Sayısı", len(uploaded_df.columns))
            with col3:
                st.metric("📁 Tablo Adı", uploaded_table)
            
            # Veri önizleme
            st.subheader("👀 Veri Önizleme")
            st.dataframe(uploaded_df.head(20))
            
            # Analiz butonu
            if st.button("🔍 Bu Veriyi Analiz Et", type="primary"):
                st.session_state.table_data = uploaded_df
                st.session_state.selected_table = uploaded_table
                st.session_state.table_analyzed = False
                st.success("✅ Veri analiz için hazırlandı!")
                st.rerun()
            
            st.markdown("---")
        
        # Tablo seçimi
        st.subheader("📋 Tablo Seçimi")
        
        try:
            # Mevcut tabloları listele
            engine = st.session_state.get('engine')
            if engine is None:
                st.error("Veritabanı bağlantısı bulunamadı. Lütfen önce bağlantı kurun.")
                return
                
            inspector = sa.inspect(engine)
            tables = inspector.get_table_names()
            
            if not tables:
                st.warning("Veritabanında tablo bulunamadı.")
                return
                
            selected_table = st.selectbox(
                "Analiz edilecek tabloyu seçin:",
                tables,
                help="Analiz etmek istediğiniz tabloyu seçin"
            )
            
            if selected_table != st.session_state.selected_table:
                st.session_state.selected_table = selected_table
                st.session_state.table_data = None
                st.session_state.analysis_results = None
                st.session_state.table_analyzed = False
                
            # Tablo analizi butonu
            if selected_table:
                if st.button("🔍 Tablo Analizini Başlat", type="primary"):
                    self._analyze_table(selected_table)
                    st.session_state.table_analyzed = True
                elif st.session_state.get('table_analyzed', False):
                    st.success("✅ Tablo analizi tamamlandı!")
                    if st.button("🔄 Yeniden Analiz Et"):
                        self._analyze_table(selected_table)
                        
            # AI analizi bölümünü ayrı göster
            if st.session_state.get('show_ai_analysis', False) and st.session_state.get('table_data') is not None:
                self._render_ai_analysis(selected_table)
                
        except Exception as e:
            st.error(f"Tablo listesi alınırken hata: {e}")
            
    def _analyze_table(self, table_name: str):
        """Tabloyu analiz et"""
        try:
            # Tablo şemasını al
            with st.spinner("Tablo analiz ediliyor..."):
                engine = st.session_state.get('engine')
                explorer = DataExplorer(engine)
                analysis = explorer.analyze_table(table_name)
                
            # Veri önizleme - EN ÜSTTE
            st.subheader("👀 Veri Önizleme")
            
            # Tablo analizi tamamlandığında otomatik olarak veri yükle
            try:
                engine = st.session_state.get('engine')
                query = f"SELECT * FROM {table_name} LIMIT 20"
                df = pd.read_sql(query, engine)
                st.dataframe(df)
                st.session_state.table_data = df
            except Exception as e:
                st.error(f"Veri yüklenirken hata: {e}")
                return
            
            # Analiz sonuçlarını göster
            st.subheader(f"📊 {table_name} Tablosu Analizi")
            
            # Tablo özeti
            columns_analysis = analysis.get('columns_analysis', {})
            text_columns = analysis.get('text_columns', [])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Toplam Kolon", len(columns_analysis))
            with col2:
                st.metric("Metin Kolonu", len(text_columns))
            with col3:
                st.metric("Toplam Satır", analysis.get('total_rows', 'N/A'))
                
            # Kolon detayları - 5'erli gruplar halinde renkli göster
            st.subheader("📝 Kolon Detayları")
            
            # Kolonları 5'erli gruplara böl
            columns_list = list(columns_analysis.items())
            for i in range(0, len(columns_list), 5):
                group = columns_list[i:i+5]
                
                # Her grup için renkli başlık
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
                group_title = f"📋 Grup {i//5 + 1} ({len(group)} kolon)"
                
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {colors[i//5 % len(colors)]}20, {colors[(i//5 + 1) % len(colors)]}20);
                    border-left: 4px solid {colors[i//5 % len(colors)]};
                    padding: 10px;
                    border-radius: 5px;
                    margin: 10px 0;
                ">
                    <h4 style="color: {colors[i//5 % len(colors)]}; margin: 0;">{group_title}</h4>
                </div>
                """, unsafe_allow_html=True)
                
                # Her gruptaki kolonları göster - Kümelendirme gibi renkli kartlar
                cols = st.columns(5)
                for j, (column_name, column_data) in enumerate(group):
                    color = colors[j % len(colors)]
                    
                    with cols[j]:
                        # Kolon kartı - Kümelendirme gibi
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, {color}20, {color}10);
                            padding: 15px;
                            border-radius: 10px;
                            margin: 5px 0;
                            border: 2px solid {color};
                            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                        ">
                            <h6 style="margin: 0; color: {color}; font-size: 14px; font-weight: bold;">
                                🔍 {column_name}
                            </h6>
                            <p style="margin: 5px 0; font-size: 11px; color: #666;">
                                📊 {column_data.get('dtype', 'N/A')}
                            </p>
                            <p style="margin: 3px 0; font-size: 10px;">
                                ❌ Null: {column_data.get('null_percentage', 0):.1f}%
                            </p>
                            <p style="margin: 3px 0; font-size: 10px;">
                                🔢 Benzersiz: {column_data.get('unique_count', 'N/A')}
                            </p>
                        """, unsafe_allow_html=True)
                        
                        # Metin kolonu ise ek bilgiler
                        if column_data.get('is_text', False):
                            text_analysis = column_data.get('text_analysis', {})
                            st.markdown(f"""
                            <div style="
                                background: {color}15;
                                padding: 8px;
                                border-radius: 5px;
                                margin-top: 5px;
                                font-size: 9px;
                            ">
                                <p style="margin: 2px 0;">📏 En kısa: {text_analysis.get('shortest_text', 'N/A')[:20]}...</p>
                                <p style="margin: 2px 0;">📏 En uzun: {text_analysis.get('longest_text', 'N/A')[:20]}...</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Örnek değerler için expander
                        sample_values = column_data.get('sample_values', [])
                        if sample_values:
                            with st.expander("📋 Örnekler", expanded=False):
                                for val in sample_values[:3]:
                                    st.markdown(f"• {str(val)[:30]}{'...' if len(str(val)) > 30 else ''}")
                        
                        # En sık kelimeler (metin kolonları için)
                        if column_data.get('is_text', False):
                            text_analysis = column_data.get('text_analysis', {})
                            most_common_words = text_analysis.get('most_common_words', [])
                            if most_common_words:
                                with st.expander("🔤 Kelimeler", expanded=False):
                                    for word, freq in most_common_words[:5]:
                                        st.markdown(f"• **{word}**: {freq}")
                    
            # AI analizi bölümünü ayrı göster
            st.session_state.show_ai_analysis = True
                
        except Exception as e:
            st.error(f"Tablo analizi hatası: {e}")
            
    def _render_ai_analysis(self, table_name: str):
        """AI analizi bölümünü göster"""
        st.subheader("🤖 AI Analizi")
        
        if not AI_HELPER_AVAILABLE:
            st.error("AI Helper modülü bulunamadı!")
            return
            
        # AI Helper'ı başlat
        if not self.ai_helper:
            try:
                self.ai_helper = AIHelper()
            except Exception as e:
                st.error(f"AI Helper başlatılamadı: {e}")
                return
                
        # Metin kolonlarını seç
        df = st.session_state.table_data
        
        # Metin kolonlarını bul
        text_columns = []
        for col in df.columns:
            if df[col].dtype == 'object':
                # Null olmayan string değerlerin oranını kontrol et
                non_null_ratio = df[col].notna().sum() / len(df)
                if non_null_ratio > 0.1:  # %10'dan fazla veri varsa
                    text_columns.append(col)
                    
        if not text_columns:
            st.warning("Analiz edilecek metin kolonu bulunamadı.")
            return
            
        # Kolon seçimi
        selected_columns = st.multiselect(
            "Analiz edilecek kolonları seçin:",
            text_columns,
            default=text_columns[:2] if len(text_columns) >= 2 else text_columns
        )
        
        if not selected_columns:
            st.warning("Lütfen en az bir kolon seçin.")
            return
            
        # Prompt düzenleme bölümü
        st.subheader("📝 AI Prompt Düzenleme")
        
        # Seçilen AI işlemine göre varsayılan prompt'u al
        ai_action = st.session_state.get('ai_action', 'Özetleme')
        default_prompt = self.ai_helper.get_default_prompt(ai_action)
        default_system_prompt = self.ai_helper.get_default_system_prompt(ai_action)
        
        # AI işlemi değiştiğinde uygun prompt'u kullan
        if 'last_ai_action' not in st.session_state or st.session_state.last_ai_action != ai_action:
            # Önce özel varsayılan prompt var mı kontrol et
            custom_defaults = st.session_state.get('custom_defaults', {})
            custom_system_defaults = st.session_state.get('custom_system_defaults', {})
            
            if ai_action in custom_defaults:
                st.session_state.custom_prompt = custom_defaults[ai_action]
            else:
                st.session_state.custom_prompt = default_prompt
                
            if ai_action in custom_system_defaults:
                st.session_state.custom_system_prompt = custom_system_defaults[ai_action]
            else:
                st.session_state.custom_system_prompt = default_system_prompt
                
            st.session_state.last_ai_action = ai_action
        
        # Mevcut prompt'u al (özel varsayılan, özel prompt veya orijinal varsayılan)
        custom_defaults = st.session_state.get('custom_defaults', {})
        custom_system_defaults = st.session_state.get('custom_system_defaults', {})
        
        if ai_action in custom_defaults:
            current_prompt = custom_defaults[ai_action]
        else:
            current_prompt = st.session_state.get('custom_prompt', default_prompt)
            
        if ai_action in custom_system_defaults:
            current_system_prompt = custom_system_defaults[ai_action]
        else:
            current_system_prompt = st.session_state.get('custom_system_prompt', default_system_prompt)
        
        # Prompt düzenleme bölümü - Div ile organize edilmiş
        st.markdown("""
        <div style="
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin: 10px 0;
        ">
        """, unsafe_allow_html=True)
        
        # Prompt'ları yan yana göster
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🤖 AI Prompt:**")
            custom_prompt = st.text_area(
                "AI Prompt'unu düzenleyin:",
                value=current_prompt,
                height=150,
                help="AI modeline gönderilecek prompt'u düzenleyebilirsiniz. {texts} yer tutucusu metinlerle değiştirilecektir.",
                key="ai_prompt"
            )
            
            # AI Prompt butonları - AI Prompt'un altında
            ai_col1, ai_col2 = st.columns(2)
            
            with ai_col1:
                if st.button("💾 Varsayılan AI Prompt Olarak Kaydet", key="save_ai_prompt", use_container_width=True):
                    # Onay mesajı göster
                    st.warning("⚠️ Bu işlem için mevcut varsayılan AI prompt'u değiştireceksiniz. Emin misiniz?")
                    if st.button("✅ Evet, AI Prompt'u Kaydet", key="confirm_ai_save"):
                        # Bu AI işlemi için özel prompt'u kalıcı varsayılan yap
                        if 'custom_defaults' not in st.session_state:
                            st.session_state.custom_defaults = {}
                        st.session_state.custom_defaults[ai_action] = custom_prompt
                        st.success(f"✅ '{ai_action}' için AI prompt kaydedildi!")
                        st.rerun()
                    
            with ai_col2:
                if st.button("🔄 Varsayılan AI Prompt'a Dön", key="reset_ai_prompt", use_container_width=True):
                    # AI prompt'a dön
                    if 'custom_defaults' in st.session_state and ai_action in st.session_state.custom_defaults:
                        del st.session_state.custom_defaults[ai_action]
                    st.session_state.custom_prompt = default_prompt
                    st.success("✅ AI prompt'a dönüldü!")
                    st.rerun()
            
        with col2:
            st.markdown("**⚙️ Sistem Prompt:**")
            custom_system_prompt = st.text_area(
                "Sistem prompt'unu düzenleyin:",
                value=current_system_prompt,
                height=150,
                help="AI modelinin rolünü ve davranışını belirleyen sistem prompt'u düzenleyebilirsiniz.",
                key="system_prompt"
            )
            
            # Sistem Prompt butonları - Sistem Prompt'un altında
            system_col1, system_col2 = st.columns(2)
            
            with system_col1:
                if st.button("💾 Varsayılan Sistem Prompt'u Olarak Kaydet", key="save_system_prompt", use_container_width=True):
                    # Onay mesajı göster
                    st.warning("⚠️ Bu işlem için mevcut varsayılan sistem prompt'u değiştireceksiniz. Emin misiniz?")
                    if st.button("✅ Evet, Sistem Prompt'u Kaydet", key="confirm_system_save"):
                        # Bu AI işlemi için özel sistem prompt'u kalıcı varsayılan yap
                        if 'custom_system_defaults' not in st.session_state:
                            st.session_state.custom_system_defaults = {}
                        st.session_state.custom_system_defaults[ai_action] = custom_system_prompt
                        st.success(f"✅ '{ai_action}' için sistem prompt kaydedildi!")
                        st.rerun()
                        
            with system_col2:
                if st.button("🔄 Varsayılan Sistem Prompt'una Dön", key="reset_system_prompt", use_container_width=True):
                    # Sistem prompt'a dön
                    if 'custom_system_defaults' in st.session_state and ai_action in st.session_state.custom_system_defaults:
                        del st.session_state.custom_system_defaults[ai_action]
                    st.session_state.custom_system_prompt = default_system_prompt
                    st.success("✅ Sistem prompt'a dönüldü!")
                    st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # AI analizi başlat
        if st.button("🚀 AI Analizini Başlat", type="primary"):
            try:
                with st.spinner("AI analizi yapılıyor..."):
                    # Seçilen kolonlardan metinleri al
                    texts = []
                    for col in selected_columns:
                        col_texts = df[col].dropna().astype(str).tolist()
                        texts.extend(col_texts[:50])  # Her kolondan max 50 metin
                        
                    if not texts:
                        st.error("Analiz edilecek metin bulunamadı.")
                        return
                        
                    # AI işlemini gerçekleştir
                    ai_model = st.session_state.get('ai_model', 'llama3:latest')
                    ai_action = st.session_state.get('ai_action', 'Özetleme')
                    custom_prompt = st.session_state.get('custom_prompt')
                    custom_system_prompt = st.session_state.get('custom_system_prompt')
                    
                    if ai_action == "Özetleme":
                        result = self.ai_helper.summarize_texts(texts, model=ai_model, custom_prompt=custom_prompt, custom_system_prompt=custom_system_prompt)
                    elif ai_action == "Sınıflandırma":
                        result = self.ai_helper.classify_texts(texts, model=ai_model, custom_prompt=custom_prompt, custom_system_prompt=custom_system_prompt)
                    elif ai_action == "Kümelendirme":
                        result = self.ai_helper.cluster_texts(texts, model=ai_model, custom_prompt=custom_prompt, custom_system_prompt=custom_system_prompt)
                    elif ai_action == "Trend Analizi":
                        # Basit tarih simülasyonu
                        dates = pd.date_range(start='2024-01-01', periods=len(texts), freq='D')
                        result = self.ai_helper.analyze_trends(texts, dates.astype(str).tolist(), model=ai_model, custom_prompt=custom_prompt, custom_system_prompt=custom_system_prompt)
                    else:
                        st.error("Geçersiz AI işlemi.")
                        return
                        
                    # Sonuçları göster
                    st.session_state.analysis_results = result
                    
                    if 'error' in result:
                        st.error(f"AI analizi hatası: {result['error']}")
                    else:
                        st.success("AI analizi tamamlandı!")
                        
                        # Analiz bilgilerini göster
                        model_used = result.get('model_used', 'Bilinmiyor')
                        processing_time = result.get('processing_time', 0)
                        texts_analyzed = result.get('texts_analyzed', 0)
                        analysis_type = result.get('analysis_type', 'AI Analizi')
                        
                        # Analiz bilgileri kartı
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("🤖 Model", model_used)
                        with col2:
                            st.metric("⏱️ Süre", f"{processing_time:.2f}s")
                        with col3:
                            st.metric("📝 Analiz Edilen", f"{texts_analyzed} metin")
                        with col4:
                            st.metric("🔍 Analiz Türü", analysis_type)
                        
                        # Sonuçları göster
                        st.subheader("📊 Analiz Sonuçları")
                        
                        if ai_action == "Özetleme":
                            st.write("**Özet:**")
                            st.write(result.get('summary', 'Özet bulunamadı.'))
                            
                        elif ai_action == "Sınıflandırma":
                            st.write("**Sınıflandırma Sonuçları:**")
                            classifications = result.get('classifications', [])
                            if classifications:
                                class_df = pd.DataFrame(classifications)
                                st.dataframe(class_df)
                                
                        elif ai_action == "Kümelendirme":
                            st.write("**Kümeleme Sonuçları:**")
                            clusters = result.get('clusters', [])
                            raw_response = result.get('raw_response', '')
                            
                            if clusters and isinstance(clusters, list):
                                # Parse edilmiş kümeleri göster - 5 sütunda
                                valid_clusters = [c for c in clusters if isinstance(c, dict)]
                                
                                if valid_clusters:
                                    # 5 sütunda kümeleri göster
                                    cols = st.columns(5)
                                    for i, cluster in enumerate(valid_clusters):
                                        cluster_name = cluster.get('name', f'Küme {i+1}')
                                        texts = cluster.get('texts', [])
                                        indices = cluster.get('text_indices', [])
                                        
                                        with cols[i % 5]:
                                            # Küme kartı
                                            st.markdown(f"""
                                            <div style="
                                                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                                padding: 12px;
                                                border-radius: 8px;
                                                margin: 5px 0;
                                                color: white;
                                                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                                min-height: 120px;
                                            ">
                                                <h5 style="margin: 0; color: white; font-size: 14px;">🔍 {cluster_name}</h5>
                                                <p style="margin: 3px 0; font-size: 12px;">📊 {len(texts)} metin</p>
                                                <p style="margin: 3px 0; font-size: 11px; opacity: 0.9;">{', '.join(map(str, [idx+1 for idx in indices[:5]]))}{'...' if len(indices) > 5 else ''}</p>
                                            </div>
                                            """, unsafe_allow_html=True)
                                            
                                            # İlk 3 metni kompakt göster
                                            for j, text in enumerate(texts[:3]):
                                                st.markdown(f"""
                                                <div style="
                                                    background: #f8f9fa;
                                                    padding: 8px;
                                                    border-radius: 6px;
                                                    border-left: 3px solid #667eea;
                                                    margin: 3px 0;
                                                    font-size: 11px;
                                                    max-height: 60px;
                                                    overflow: hidden;
                                                ">
                                                    <strong>#{indices[j]+1 if j < len(indices) else j+1}</strong><br>
                                                    {text[:50]}{'...' if len(text) > 50 else ''}
                                                </div>
                                                """, unsafe_allow_html=True)
                                            
                                            # Daha fazla metin varsa expander
                                            if len(texts) > 3:
                                                with st.expander(f"+{len(texts)-3} daha"):
                                                    for j in range(3, min(len(texts), 8)):
                                                        st.markdown(f"**{indices[j]+1 if j < len(indices) else j+1}:** {texts[j][:60]}{'...' if len(texts[j]) > 60 else ''}")
                                    
                                    # 5'ten fazla küme varsa yeni satır
                                    if len(valid_clusters) > 5:
                                        st.markdown("---")
                                        st.write(f"**Diğer {len(valid_clusters)-5} küme:**")
                                        remaining_cols = st.columns(5)
                                        for i, cluster in enumerate(valid_clusters[5:]):
                                            cluster_name = cluster.get('name', f'Küme {i+6}')
                                            texts = cluster.get('texts', [])
                                            indices = cluster.get('text_indices', [])
                                            
                                            with remaining_cols[i % 5]:
                                                st.markdown(f"""
                                                <div style="
                                                    background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                                                    padding: 10px;
                                                    border-radius: 8px;
                                                    margin: 3px 0;
                                                    color: white;
                                                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                                ">
                                                    <h6 style="margin: 0; color: white; font-size: 12px;">🔍 {cluster_name}</h6>
                                                    <p style="margin: 2px 0; font-size: 10px;">📊 {len(texts)} metin</p>
                                                </div>
                                                """, unsafe_allow_html=True)
                                    # Ham metin gösterilmesin - sadece JSON expander'da görünsün
                            else:
                                # Ham yanıtı göster
                                st.write("**Ham Yanıt:**")
                                st.text_area("AI Yanıtı", raw_response, height=200)
                                
                                # Parse edilemeyen durumda yardım
                                st.info("💡 Kümelendirme sonuçları parse edilemedi. Ham yanıt yukarıda gösteriliyor.")
                                            
                        elif ai_action == "Trend Analizi":
                            st.write("**Trend Analizi Sonuçları:**")
                            trends = result.get('trends', '')
                            if trends:
                                if isinstance(trends, dict):
                                    # Dictionary ise items() ile döngü
                                    for trend_type, description in trends.items():
                                        st.write(f"**{trend_type}:** {description}")
                                else:
                                    # String ise direkt göster
                                    st.write(trends)
                                    
                        # JSON formatında da göster
                        with st.expander("🔧 JSON Sonuç"):
                            st.json(result)
                            
            except Exception as e:
                st.error(f"AI analizi hatası: {e}")
                
    def render_footer(self):
        """Footer'ı göster"""
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666;'>
            <p>🔍 VeriKeşif - AI Destekli Talep Analizi Platformu</p>
            <p>Geliştirici: <a href="https://github.com/Zaferturan" target="_blank" style="color: #0066cc; text-decoration: none;">Zafer TURAN</a> | Versiyon: 1.0</p>
        </div>
        """, unsafe_allow_html=True)

def main():
    """Ana uygulama fonksiyonu"""
    # CSS stilleri - KAPSAMLI ÜST BOŞLUK KALDIRMA
    st.markdown("""
    <style>
        /* EN GÜÇLÜ CSS - TÜM ÜST BOŞLUKLARI KALDIR */
        
        /* 1. Streamlit'in tüm header'ını tamamen kaldır */
        .stApp > header,
        .stApp > header *,
        .stApp > div:first-child > header,
        .stApp > div:first-child > header *,
        .stApp > div > header,
        .stApp > div > header *,
        .stApp > div > div > header,
        .stApp > div > div > header * {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            height: 0 !important;
            width: 0 !important;
            overflow: hidden !important;
            position: absolute !important;
            left: -9999px !important;
            top: -9999px !important;
            pointer-events: none !important;
        }
        
        /* 2. Ana container'ın tüm üst boşluklarını kaldır */
        .main .block-container,
        .main .block-container *,
        .main > div,
        .main > div * {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        
        /* 3. Sidebar'ın üst boşluklarını kaldır */
        .css-1d391kg,
        .css-1d391kg *,
        .sidebar .sidebar-content,
        .sidebar .sidebar-content * {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        
        /* 4. Tüm sayfa seviyesi boşlukları kaldır */
        .stApp,
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        
        /* 5. Özel olarak ilk div'lerin boşluklarını kaldır */
        .stApp > div:first-child,
        .stApp > div:first-child > div:first-child,
        .main > div:first-child,
        .main > div:first-child > div:first-child {
            padding-top: 0 !important;
            margin-top: 0 !important;
            height: auto !important;
            min-height: 0 !important;
        }
        
        /* 6. Tüm elementlerin üst margin'lerini sıfırla */
        * {
            margin-top: 0 !important;
        }
        
        /* 6.5. Streamlit'in kendi CSS'ini override et */
        .stApp > div:first-child {
            padding-top: 0 !important;
            margin-top: 0 !important;
            height: auto !important;
            min-height: 0 !important;
        }
        
        /* 6.6. Main container'ı tamamen yukarı taşı */
        .main .block-container {
            padding-top: 0 !important;
            margin-top: 0 !important;
            padding-bottom: 1rem !important;
        }
        
        /* 6.7. Tüm div'lerin üst boşluklarını kaldır */
        div {
            margin-top: 0 !important;
        }
        
        /* 6.8. Özel olarak ilk elementleri hedefle */
        .stApp > div:first-child,
        .stApp > div:first-child > div:first-child,
        .stApp > div:first-child > div:first-child > div:first-child {
            padding-top: 0 !important;
            margin-top: 0 !important;
            height: auto !important;
            min-height: 0 !important;
        }
        
        /* 6.9. Tüm olası boşlukları kaldır - EN GÜÇLÜ */
        .stApp,
        .stApp *,
        .stApp > div,
        .stApp > div *,
        .stApp > div > div,
        .stApp > div > div *,
        .stApp > div > div > div,
        .stApp > div > div > div * {
            margin-top: 0 !important;
        }
        
        /* 6.10. Özel olarak padding'leri de kaldır */
        .stApp,
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div {
            padding-top: 0 !important;
        }
        
        /* 6.11. Body ve html elementlerini de hedefle */
        body, html {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        
        /* 7. Özel olarak logo ve başlık için */
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-top: 0 !important;
            padding-top: 0 !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* 8. Logo container'ı için */
        .stImage {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        
        /* 9. Sağ üst menüleri gizle */
        #MainMenu {
            visibility: hidden !important;
        }
        
        /* 10. Sidebar toggle butonunu koru - BASİT VE ETKİLİ */
        [data-testid="collapsedControl"] {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            position: fixed !important;
            top: 10px !important;
            left: 10px !important;
            z-index: 9999 !important;
            background-color: #1f77b4 !important;
            color: white !important;
            border-radius: 50% !important;
            width: 40px !important;
            height: 40px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
            font-size: 16px !important;
            cursor: pointer !important;
        }
        
        /* 11. Sidebar toggle butonuna hover efekti */
        [data-testid="collapsedControl"]:hover {
            background-color: #1565c0 !important;
            transform: scale(1.1) !important;
        }
        /* Deploy butonunu ve geliştirme öğelerini tamamen kaldır */
        .stDeployButton,
        .stDeployButton > *,
        [data-testid="stDeployButton"],
        [data-testid="stDeployButton"] > *,
        .stApp > header [data-testid="stDeployButton"],
        .stApp > header .stDeployButton,
        .stApp > header button[data-testid="stDeployButton"],
        .stApp > header button.stDeployButton,
        .stApp > header a[data-testid="stDeployButton"],
        .stApp > header a.stDeployButton,
        /* Geliştirme öğelerini kaldır */
        [data-testid="stToolbar"],
        [data-testid="stToolbar"] > *,
        .stApp > header [data-testid="stToolbar"],
        .stApp > header [data-testid="stToolbar"] > *,
        /* File change, Rerun, Always rerun butonları */
        [data-testid="stToolbar"] button,
        [data-testid="stToolbar"] a,
        [data-testid="stToolbar"] span,
        /* Tüm toolbar içeriği */
        .stApp > header [data-testid="stToolbar"] * {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            position: absolute !important;
            left: -9999px !important;
            top: -9999px !important;
        }


        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
        }
        .success-box {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
        .error-box {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    app = StreamlitApp()
    app.init_session_state()
    
    # Sidebar
    app.render_sidebar()
    
    # Header - doğrudan burada render et
    col1, col2 = st.columns([1, 4])
    
    with col1:
        try:
            st.image("logo.png", width=80)
        except:
            st.markdown("🔍")  # Logo yoksa emoji göster
            
    with col2:
        st.markdown('<h1 class="main-header">🔍 Nilüfer Kaşif - AI Destekli Veri Analizi</h1>', 
                   unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Ana içerik - geliştirme sürecinde auth kontrolü yok
    if st.session_state.get('connection_established', False):
        app.render_main_content()
    else:
        # Bağlantı kurulmadığında ana içerik alanında bilgi göster
        st.info("👈 Sol taraftaki sidebar'dan veritabanı bağlantısı kurun.")
    
    # Footer
    app.render_footer()

if __name__ == "__main__":
    main() 