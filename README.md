# 🚀 VeriKeşif – Yapay Zeka Destekli Talep Analiz Platformu

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge&logo=opensourceinitiative&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-24%20passed-brightgreen.svg?style=for-the-badge&logo=testinglibrary&logoColor=white)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success.svg?style=for-the-badge&logo=vercel&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Web%20App-red.svg?style=for-the-badge&logo=streamlit&logoColor=white)
![AI](https://img.shields.io/badge/AI-Powered-orange.svg?style=for-the-badge&logo=openai&logoColor=white)

[![GitHub stars](https://img.shields.io/github/stars/Zaferturan/ai_veri_analizi?style=social)](https://github.com/Zaferturan/ai_veri_analizi/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Zaferturan/ai_veri_analizi?style=social)](https://github.com/Zaferturan/ai_veri_analizi/network)
[![GitHub issues](https://img.shields.io/github/issues/Zaferturan/ai_veri_analizi)](https://github.com/Zaferturan/ai_veri_analizi/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/Zaferturan/ai_veri_analizi)](https://github.com/Zaferturan/ai_veri_analizi/pulls)

</div>

> **VeriKeşif**, kullanıcı taleplerini ve önerilerini analiz etmek için geliştirilmiş, yapay zeka destekli bir veri analiz platformudur. MySQL veritabanlarından veri keşfi yapar, Ollama yerel AI modelleri ile metin analizi gerçekleştirir ve performans metriklerini izler.

<div align="center">

### 🌟 **Öne Çıkan Özellikler**

| 🔐 **Güvenlik** | 📊 **Veri Analizi** | 🤖 **AI Destekli** | 📈 **Performans** |
|:---:|:---:|:---:|:---:|
| JWT Token Yönetimi | MySQL Tablo Analizi | Ollama Yerel AI | Embedding Cache |
| Rol Tabanlı Erişim | Veri Kalitesi Kontrolü | Türkçe Prompt Sistemi | Prometheus Metrikler |
| Şifre Hashleme | Metin Kolonu Tespiti | Çoklu Model Desteği | Gerçek Zamanlı İzleme |

</div>

## 📌 Proje Tanımı

VeriKeşif, kurumların müşteri geri bildirimlerini, talep ve önerilerini analiz etmek için tasarlanmış kapsamlı bir platformdur. Sistem şu temel bileşenlerden oluşur:

- **🔐 Kimlik Doğrulama Sistemi**: Rol tabanlı erişim kontrolü
- **📊 Veri Keşif Modülü**: MySQL tablolarının otomatik analizi
- **🧠 AI Destekli Analiz**: Ollama yerel AI modelleri entegrasyonu
- **💾 Embedding Cache**: Performans optimizasyonu
- **📈 Metrik İzleme**: Prometheus uyumlu performans takibi

## 🧰 Sistem Özellikleri

### 🔐 Kimlik Doğrulama ve Yetkilendirme
- **Rol Tabanlı Erişim**: `admin`, `analyst`, `viewer` rolleri
- **JWT Token Yönetimi**: Güvenli oturum yönetimi
- **Şifre Hashleme**: bcrypt ile güvenli şifre saklama
- **CLI ve API**: Hem komut satırı hem REST API desteği

### 📊 Veri Keşif Sistemi
- **MySQL Tablo Analizi**: Kapsamlı veri keşif
- **Kolon Şema Tespiti**: Veri tipleri ve özellikler
- **Veri Kalitesi Analizi**: Null oranları ve benzersizlik
- **Metin Kolonu Tespiti**: NLP için uygun alanlar
- **Kelime Frekans Analizi**: En sık geçen kelimeler
- **JSON Rapor Dışa Aktarma**: Detaylı analiz sonuçları

### 🤖 AI Destekli Analiz Sistemi
- **Metin Özetleme**: Ollama yerel AI modelleri ile akıllı özetleme
- **Metin Kümeleme**: Benzer içerikleri gruplandırma
- **Metin Sınıflandırma**: Kategori bazlı sınıflandırma
- **Trend Analizi**: Zaman içindeki değişimleri analiz etme
- **Çoklu Model Desteği**: Ollama yerel modelleri (llama3, qwen2.5, mistral)
- **Türkçe Prompt Sistemi**: Özelleştirilebilir Türkçe prompt'lar
- **Embedding Cache Entegrasyonu**: Performans optimizasyonu
- **Metrics İzleme**: Prometheus uyumlu metrik toplama
- **JSON Sonuç Dışa Aktarma**: Analiz sonuçlarını kaydetme

### 💾 Embedding Cache Sistemi
- **Performans Optimizasyonu**: Gereksiz API çağrılarını önleme
- **Çoklu Model Desteği**: Farklı embedding modelleri
- **Cache İstatistikleri**: Hit/miss oranları ve kullanım analizi
- **Otomatik Temizlik**: Eski cache kayıtlarının temizlenmesi
- **CLI Arayüzü**: Kolay kullanım

### 📈 Prometheus Metrik İzleme Sistemi
- **AI Çağrı İzleme**: Model bazlı çağrı sayısı ve süre takibi
- **Token Kullanımı**: API token tüketimi izleme
- **Hata Oranları**: Başarısız çağrıların analizi
- **Performans Metrikleri**: Yanıt süresi histogramları
- **Prometheus Uyumlu**: Standart metrik formatı
- **HTTP Endpoint**: `/metrics` endpoint ile erişim
- **JSON Dışa Aktarma**: Metrik verilerini kaydetme

### 🖥️ Streamlit Web Arayüzü
- **Kullanıcı Dostu Arayüz**: Sürükle-bırak ve tıklama ile kolay kullanım
- **Çoklu Veritabanı Desteği**: MySQL, SQLite, PostgreSQL
- **Görsel Tablo Analizi**: Kolon detayları ve istatistikler
- **AI Analiz Entegrasyonu**: Web arayüzünden AI fonksiyonları
- **Gerçek Zamanlı Cache Durumu**: Embedding cache istatistikleri
- **Canlı Metrik İzleme**: AI çağrı metriklerini görüntüleme
- **Responsive Tasarım**: Mobil ve masaüstü uyumlu
- **Session Yönetimi**: Kullanıcı oturumu koruma

## 🚀 Kurulum Adımları

### Gereksinimler
- **Python**: 3.8 veya üzeri
- **MySQL**: Veri kaynağı için
- **Ollama**: Yerel AI modelleri için (opsiyonel)

### 1. Projeyi İndirin
```bash
git clone <repository-url>
cd istek_oneri_analizi
```

### 2. Python Sanal Ortamı Oluşturun
```bash
# Python 3.10 ile sanal ortam oluşturun
python3.10 -m venv .env/venv

# Sanal ortamı aktifleştirin
source .env/venv/bin/activate  # Linux/Mac
# veya
.env\venv\Scripts\activate     # Windows
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Ortam Değişkenlerini Ayarlayın
```bash
# .env dosyası oluşturun
cp example.env .env

# .env dosyasını düzenleyin
nano .env
```

**Önemli:** `.env` dosyasında şu bilgileri güncelleyin:
- `MYSQL_PASSWORD`: MySQL şifreniz
- `POSTGRES_PASSWORD`: PostgreSQL şifreniz  
- `JWT_SECRET_KEY`: JWT için güvenli bir anahtar

### 5. Örnek Kullanıcılar Oluşturun
```bash
python auth.py --create-samples
```

## 🔐 Kullanıcı Girişi ve Rol Sistemi

### Kullanıcı Rolleri
- **👑 Admin**: Tam sistem yönetimi
- **🔬 Analyst**: Veri analizi ve AI fonksiyonları
- **👁️ Viewer**: Sadece görüntüleme yetkisi

### CLI ile Giriş
```bash
python auth.py
```

**Menü Seçenekleri:**
1. **Kullanıcı Kaydı**: Yeni kullanıcı oluşturma
2. **Kullanıcı Girişi**: Mevcut kullanıcı ile giriş
3. **Kullanıcı Listesi**: Tüm kullanıcıları görüntüleme
4. **Kullanıcı Silme**: Kullanıcı silme (sadece admin)
5. **API Sunucusunu Başlat**: REST API'yi başlatma
6. **Çıkış**: Programdan çıkış

### API ile Giriş
```bash
# API sunucusunu başlat
python auth.py --api
```

**API Endpoints:**
```bash
# Kullanıcı kaydı
curl -X POST "http://localhost:8000/register" \
     -H "Content-Type: application/json" \
     -d '{"username": "analyst1", "password": "password123", "role": "analyst"}'

# Kullanıcı girişi
curl -X POST "http://localhost:8000/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "analyst1", "password": "password123"}'

# Kullanıcı bilgilerini getir
curl -X GET "http://localhost:8000/me" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 📊 Veritabanı Keşfi ve Örnek Kullanım

### MySQL Bağlantısı
```python
from explorer import DataExplorer
from sqlalchemy import create_engine

# MySQL bağlantısı
engine = create_engine('mysql+pymysql://user:password@localhost/database')

# DataExplorer oluştur
explorer = DataExplorer(engine)
```

### Tablo Analizi
```bash
# CLI ile tablo analizi
python explorer.py --host localhost --user root --password mypass --database mydb --table customer_feedback
```

### Programatik Kullanım
```python
# Tablo şemasını al
schema = explorer.get_table_schema("customer_feedback")
print(f"Kolonlar: {schema}")

# Detaylı analiz yap
analysis = explorer.analyze_table("customer_feedback")
print(f"Analiz sonucu: {analysis}")

# Metin kolonlarını bul
text_columns = explorer.get_text_columns(schema)
print(f"Metin kolonları: {text_columns}")
```

## 🧠 AI Fonksiyonları

### Metin Özetleme
```python
from ai_helper import AIHelper

# AI Helper başlat
ai_helper = AIHelper()

# Metin özetleme
texts = ["Uzun metin 1...", "Uzun metin 2..."]
summary = ai_helper.summarize_texts(texts, model="llama3:latest")
print(f"Özet: {summary['summary']}")
```

### Metin Kümeleme
```python
# Metin kümeleme
clusters = ai_helper.cluster_texts(texts, model="qwen2.5-coder:32b-instruct-q4_0")
for cluster in clusters['clusters']:
    print(f"Grup: {cluster['name']} - Metinler: {cluster['text_indices']}")
```

### Metin Sınıflandırma
```python
# Metin sınıflandırma
categories = ["Teknik", "Genel", "Şikayet", "Öneri"]
classification = ai_helper.classify_texts(texts, model="mistral:latest")
for item in classification['classifications']:
    print(f"Metin {item['text_index']}: {item['category']}")
```

### Trend Analizi
```python
# Trend analizi
dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
trends = ai_helper.analyze_trends(texts, dates, model="llama3:latest")
print(f"Trendler: {trends['trends']}")
```

### CLI Kullanımı
```bash
# Metin özetleme
python ai_helper.py --action summarize --texts "Metin 1" "Metin 2" --model llama3:latest

# Metin kümeleme
python ai_helper.py --action cluster --texts "Metin 1" "Metin 2" "Metin 3" --model qwen2.5-coder:32b-instruct-q4_0

# Metin sınıflandırma
python ai_helper.py --action classify --texts "Teknik metin" "Genel metin" --model mistral:latest

# Trend analizi
python ai_helper.py --action trends --texts "Metin 1" "Metin 2" --dates "2024-01-01" "2024-01-02"
```

## 💾 Embedding Cache Sistemi

### CLI Kullanımı
```bash
# Tek metin embed et
python embedding_cache.py --text "Merhaba dünya"

# Dosya embed et
python embedding_cache.py --file "sample_text.txt"

# Cache istatistiklerini göster
python embedding_cache.py --stats

# Cache'i temizle
python embedding_cache.py --clear
```

### Programatik Kullanım
```python
from embedding_cache import EmbeddingCache

# Embedding cache oluştur
cache = EmbeddingCache()

# Metin embed et
embedding = cache.get_embedding("Merhaba dünya")
print(f"Embedding boyutu: {embedding.shape}")

# Cache istatistikleri
stats = cache.get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.2f}%")

# AI Helper ile entegrasyon
ai_helper = AIHelper()
ai_helper.set_embedding_cache(cache)
```

## 📈 Metrik İzleme (Prometheus)

### CLI Kullanımı
```bash
# Metrik sunucusunu başlat
python metrics.py --action start-server --port 9000

# Metrik özetini göster
python metrics.py --action summary

# Test metrikleri oluştur
python metrics.py --action test

# Metrikleri dışa aktar
python metrics.py --action export --output metrics.json

# Metrikleri sıfırla
python metrics.py --action reset
```

### Programatik Kullanım
```python
from metrics import (
    log_ai_call, 
    track_ai_call, 
    start_metrics_server, 
    get_metrics_summary,
    export_metrics
)

# Manuel metrik loglama
log_ai_call("openai", "summarize", tokens_used=100, latency=1.5)

# Otomatik metrik izleme (context manager)
with track_ai_call("openai", "summarize"):
    # AI çağrısı burada yapılır
    result = ai_helper.summarize_texts(texts)

# Metrik sunucusunu başlat
start_metrics_server(port=9000)

# Metrik özetini al
summary = get_metrics_summary()
print(f"Toplam çağrı: {summary['stats']['total_calls']}")

# Metrikleri dışa aktar
export_metrics("metrics_export.json")
```

## 🖥️ Streamlit Web Arayüzü

### Uygulamayı Başlatma
```bash
# Demo script ile başlat
python demo_streamlit.py

# Veya doğrudan streamlit ile
streamlit run streamlit_app.py --server.port 8501
```

### Kullanım Adımları

#### 1. Veritabanı Bağlantısı
- Sol sidebar'dan veritabanı türünü seçin (MySQL, SQLite, PostgreSQL)
- **Otomatik Bağlantı**: Kullanıcı adı ve şifre `.env` dosyasından otomatik alınır
- **Veritabanı Seçimi**: Dropdown menüden mevcut veritabanlarını seçin
- "Bağlan" butonuna tıklayın

**Not:** `.env` dosyasında veritabanı bilgilerinizi güncellemeyi unutmayın!

#### 2. Tablo Seçimi ve Analizi
- Mevcut tablolar listesinden analiz edilecek tabloyu seçin
- Tablo analizi otomatik olarak başlar:
  - Kolon sayısı ve türleri
  - Null oranları
  - Metin kolonu tespiti
  - Örnek veriler
  - En sık kelimeler

#### 3. AI Analizi
- AI modelini seçin (Ollama yerel modelleri)
- AI işlemini seçin:
  - **Özetleme**: Metinleri kısa özetlere dönüştürme
  - **Sınıflandırma**: Metinleri kategorilere ayırma
  - **Kümelendirme**: Benzer metinleri gruplandırma
  - **Trend Analizi**: Zaman bazlı analiz
- Analiz edilecek kolonları seçin
- "AI Analizi Başlat" butonuna tıklayın

#### 4. Sonuçları İnceleme
- Analiz sonuçları ana sayfada görüntülenir
- JSON formatında detaylı sonuçlar için expander'ı açın
- Sonuçları kaydetmek için JSON formatını kopyalayın

#### 5. Cache ve Metrikler
- **Cache Durumu**: Sidebar'da embedding cache istatistikleri
- **Metrikler**: AI çağrı sayısı ve token kullanımı
- **Cache Temizleme**: Eski cache kayıtlarını temizleme
- **Metrik Sıfırlama**: İstatistikleri sıfırlama

### Özellikler
- **Responsive Tasarım**: Mobil ve masaüstü uyumlu
- **Session Yönetimi**: Kullanıcı oturumu koruma
- **Gerçek Zamanlı Güncelleme**: Cache ve metrik durumu
- **Hata Yönetimi**: Kullanıcı dostu hata mesajları
- **Performans Optimizasyonu**: Lazy loading ve caching

### Prometheus Entegrasyonu
Metrik sunucusu başlatıldıktan sonra, Prometheus ile uyumlu metrikler şu adresten erişilebilir:
```
http://localhost:9000/metrics
```

**Mevcut Metrikler:**
- `ai_calls_total`: Toplam AI çağrı sayısı (model, action etiketli)
- `ai_tokens_total`: Toplam token kullanımı (model, action etiketli)
- `ai_latency_seconds`: Yanıt süresi histogramı (model, action etiketli)
- `ai_active_requests`: Aktif istek sayısı (model, action etiketli)
- `ai_errors_total`: Toplam hata sayısı (model, action, error_type etiketli)

## 🧪 Testler

### Tüm Testleri Çalıştır
```bash
# Tüm testleri çalıştır
pytest -v

# Belirli modül testleri
pytest test_auth.py -v
pytest test_embedding_cache.py -v
pytest test_explorer.py -v
pytest test_ai_helper.py -v
pytest test_metrics.py -v
```

### Belirli Testleri Çalıştır
```bash
# Belirli test sınıfını çalıştır
pytest test_auth.py::TestAuthSystem -v

# Belirli testi çalıştır
pytest test_auth.py::TestAuthSystem::test_user_login -v

# Test coverage ile çalıştır
pytest --cov=. --cov-report=html
```

## 📁 Proje Yapısı

```
istek_oneri_analizi/
├── auth.py                    # Kimlik doğrulama sistemi
├── embedding_cache.py         # Embedding cache sistemi
├── explorer.py               # Veri keşif sistemi
├── ai_helper.py              # AI destekli analiz sistemi
├── metrics.py                # Prometheus metrik izleme sistemi
├── test_auth.py              # Auth test dosyası
├── test_embedding_cache.py   # Embedding cache test dosyası
├── test_explorer.py          # Veri keşif test dosyası
├── test_ai_helper.py         # AI Helper test dosyası
├── test_metrics.py           # Metrics test dosyası
├── requirements.txt          # Python bağımlılıkları
├── README.md                # Bu dosya
├── users.db                 # Auth SQLite veritabanı
├── embedding_cache.db       # Embedding cache SQLite veritabanı
├── .env/                    # Python sanal ortam
│   └── venv/
├── docs/                    # Dokümantasyon
│   └── ROADMAP.md           # Proje yol haritası
└── streamlit_app.py         # Streamlit web arayüzü
```

## 🔧 Yapılandırma

### Ortam Değişkenleri
```bash
# Veritabanı Ayarları
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=password
DB_NAME=database

# Metrik Sunucusu
METRICS_PORT=9000
METRICS_HOST=0.0.0.0
```

### Örnek Yapılandırma Dosyası
```bash
# example.env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=mypassword
DB_NAME=customer_feedback
METRICS_PORT=9000
```

## 🚨 Sorun Giderme

### Yaygın Sorunlar

**1. Prometheus Client Hatası**
```bash
# Hata: ModuleNotFoundError: No module named 'prometheus_client'
pip install prometheus_client
```

**2. MySQL Bağlantı Hatası**
```bash
# Hata: ModuleNotFoundError: No module named 'pymysql'
pip install pymysql
```

**3. Ollama Bağlantı Hatası**
```bash
# Hata: Ollama bağlantısı kurulamadı
# Çözüm: Ollama servisinin çalıştığından emin olun
ollama serve
```

**4. Embedding Model Yükleme Hatası**
```bash
# Hata: İnternet bağlantısı gerekli
# Çözüm: İnternet bağlantınızı kontrol edin
# Alternatif: Offline model kullanın
```

### Log Dosyaları
```bash
# Log seviyesini değiştir
export LOG_LEVEL=DEBUG

# Logları dosyaya yönlendir
python auth.py > auth.log 2>&1
```

## 📈 Performans Optimizasyonu

### Embedding Cache Kullanımı
```python
# Cache kullanarak performansı artır
cache = EmbeddingCache()
ai_helper.set_embedding_cache(cache)
```

### Metrik İzleme
```python
# Performans metriklerini izle
with track_ai_call("openai", "summarize"):
    result = ai_helper.summarize_texts(texts)
```

### Batch İşleme
```python
# Büyük veri setleri için batch işleme
for batch in text_batches:
    with track_ai_call("openai", "summarize"):
        results = ai_helper.summarize_texts(batch)
```

## 🤝 Katkı Sağlama

### Geliştirme Ortamı Kurulumu
```bash
# Fork yapın ve clone edin
git clone https://github.com/your-username/istek_oneri_analizi.git
cd istek_oneri_analizi

# Geliştirme branch'i oluşturun
git checkout -b feature/new-feature

# Değişikliklerinizi commit edin
git add .
git commit -m "Add new feature"

# Pull request gönderin
git push origin feature/new-feature
```

### Test Yazma
```python
# Yeni test ekleyin
def test_new_feature():
    """Yeni özellik testi"""
    # Test kodunuz burada
    assert True
```

### Dokümantasyon Güncelleme
- README.md dosyasını güncelleyin
- Yeni özellikler için örnekler ekleyin
- API dokümantasyonunu güncelleyin

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 📞 İletişim

- **Proje Sahibi**: Zafer TURAN
- **E-posta**: zaferturan@gmail.com
- **GitHub**: [@Zaferturan](https://github.com/Zaferturan)
- **Issues**: [GitHub Issues](https://github.com/Zaferturan/ai_veri_analizi/issues)

## 🙏 Teşekkürler

- **Ollama**: Yerel AI modelleri için
- **Prometheus**: Metrik izleme için
- **SQLAlchemy**: Veritabanı ORM için
- **FastAPI**: Web framework için

---

**🎉 VeriKeşif ile veri analizinizi bir üst seviyeye taşıyın!**

> Bu platform, kurumların müşteri geri bildirimlerini daha etkili analiz etmelerine ve yapay zeka destekli içgörüler elde etmelerine yardımcı olur. 