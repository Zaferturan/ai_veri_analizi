"""
Streamlit Uygulaması Demo Script

Bu script, streamlit_app.py uygulamasını demo amaçlı çalıştırır.
Kullanıcıların uygulamayı nasıl başlatacaklarını gösterir.

Kullanım:
    python demo_streamlit.py
"""

import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """Gerekli bağımlılıkları kontrol et"""
    required_packages = [
        'streamlit',
        'pandas',
        'sqlalchemy',
        'pymysql',
        'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    # PostgreSQL opsiyonel olarak kontrol et
    try:
        import psycopg2
    except ImportError:
        print("⚠️  PostgreSQL desteği için psycopg2-binary kurulmamış (opsiyonel)")
    
    if missing_packages:
        print("❌ Eksik bağımlılıklar:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Kurulum için:")
        print("   pip install -r requirements.txt")
        return False
    
    print("✅ Tüm bağımlılıklar mevcut!")
    return True

def check_modules():
    """Proje modüllerini kontrol et"""
    required_modules = [
        'auth',
        'explorer', 
        'ai_helper',
        'embedding_cache',
        'metrics'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print("⚠️  Eksik modüller:")
        for module in missing_modules:
            print(f"   - {module}.py")
        print("\n💡 Bu modüller olmadan bazı özellikler çalışmayabilir.")
        return False
    
    print("✅ Tüm modüller mevcut!")
    print("\n📋 Kurulum Kontrol Listesi:")
    print("   □ .env dosyası oluşturuldu mu? (example.env'yi .env olarak kopyalayın)")
    print("   □ Veritabanı bağlantı bilgileri girildi mi?")
    print("   □ API anahtarları eklendi mi?")
    return True

def start_streamlit():
    """Streamlit uygulamasını başlat"""
    print("🚀 Streamlit uygulaması başlatılıyor...")
    print("📱 Tarayıcınızda http://localhost:8501 adresini açın")
    print("⏹️  Durdurmak için Ctrl+C tuşlayın")
    print("-" * 50)
    
    try:
        # Streamlit uygulamasını çalıştır
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "streamlit_app.py",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 Uygulama durduruldu.")
    except Exception as e:
        print(f"❌ Hata: {e}")

def show_usage_instructions():
    """Kullanım talimatlarını göster"""
    print("📖 VeriKeşif Streamlit Uygulaması Kullanım Talimatları")
    print("=" * 60)
    print()
    print("1️⃣  Veritabanı Bağlantısı:")
    print("   - Sol sidebar'dan veritabanı türünü seçin")
    print("   - Bağlantı bilgilerini girin")
    print("   - 'Bağlan' butonuna tıklayın")
    print()
    print("2️⃣  Tablo Seçimi:")
    print("   - Mevcut tablolar listesinden birini seçin")
    print("   - Tablo analizi otomatik olarak başlar")
    print()
    print("3️⃣  AI Analizi:")
    print("   - AI modelini seçin (OpenAI/Gemini)")
    print("   - AI işlemini seçin (Özetleme/Sınıflandırma/Kümelendirme)")
    print("   - Analiz edilecek kolonları seçin")
    print("   - 'AI Analizi Başlat' butonuna tıklayın")
    print()
    print("4️⃣  Sonuçları İnceleme:")
    print("   - Analiz sonuçları ana sayfada görüntülenir")
    print("   - JSON formatında detaylı sonuçlar için expander'ı açın")
    print()
    print("5️⃣  Cache ve Metrikler:")
    print("   - Sidebar'da cache durumunu görebilirsiniz")
    print("   - AI çağrı metriklerini takip edebilirsiniz")
    print()

def main():
    """Ana fonksiyon"""
    print("🔍 VeriKeşif - Streamlit Demo")
    print("=" * 40)
    print()
    
    # Bağımlılıkları kontrol et
    if not check_dependencies():
        return
    
    print()
    
    # Modülleri kontrol et
    check_modules()
    
    print()
    
    # Kullanım talimatlarını göster
    show_usage_instructions()
    
    # Kullanıcıdan onay al
    response = input("Streamlit uygulamasını başlatmak istiyor musunuz? (y/n): ")
    
    if response.lower() in ['y', 'yes', 'evet', 'e']:
        start_streamlit()
    else:
        print("👋 Demo iptal edildi.")

if __name__ == "__main__":
    main() 