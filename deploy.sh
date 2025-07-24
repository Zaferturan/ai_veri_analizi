#!/bin/bash

# VeriKeşif - Production Deployment Script
# Bu script uygulamayı production ortamında çalıştırır

set -e

echo "🚀 VeriKeşif - Production Deployment Başlatılıyor..."

# Renkli çıktı için
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Gerekli dizinleri oluştur
echo -e "${BLUE}📁 Gerekli dizinler oluşturuluyor...${NC}"
mkdir -p data logs grafana/dashboards grafana/datasources

# Environment dosyasını kontrol et
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env dosyası bulunamadı. Örnek dosya oluşturuluyor...${NC}"
    cp example.env .env
    echo -e "${YELLOW}📝 Lütfen .env dosyasını düzenleyin ve tekrar çalıştırın.${NC}"
    exit 1
fi

# Docker'ın çalışıp çalışmadığını kontrol et
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker bulunamadı. Lütfen Docker'ı yükleyin.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose bulunamadı. Lütfen Docker Compose'u yükleyin.${NC}"
    exit 1
fi

# Eski container'ları temizle
echo -e "${BLUE}🧹 Eski container'lar temizleniyor...${NC}"
docker-compose down --remove-orphans

# Docker image'larını build et
echo -e "${BLUE}🔨 Docker image'ları build ediliyor...${NC}"
docker-compose build --no-cache

# Servisleri başlat
echo -e "${BLUE}🚀 Servisler başlatılıyor...${NC}"
docker-compose up -d

# Servislerin başlamasını bekle
echo -e "${BLUE}⏳ Servislerin başlaması bekleniyor...${NC}"
sleep 30

# Health check
echo -e "${BLUE}🏥 Health check yapılıyor...${NC}"

# VeriKeşif uygulaması
if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ VeriKeşif uygulaması çalışıyor: http://localhost:8501${NC}"
else
    echo -e "${RED}❌ VeriKeşif uygulaması başlatılamadı${NC}"
fi

# MySQL
if docker-compose exec -T mysql mysqladmin ping -h localhost --silent; then
    echo -e "${GREEN}✅ MySQL veritabanı çalışıyor${NC}"
else
    echo -e "${RED}❌ MySQL veritabanı başlatılamadı${NC}"
fi

# Ollama
if curl -f http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama AI servisi çalışıyor: http://localhost:11434${NC}"
else
    echo -e "${YELLOW}⚠️  Ollama AI servisi başlatılamadı (opsiyonel)${NC}"
fi

# Prometheus
if curl -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Prometheus metrik servisi çalışıyor: http://localhost:9090${NC}"
else
    echo -e "${YELLOW}⚠️  Prometheus metrik servisi başlatılamadı${NC}"
fi

# Grafana
if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Grafana dashboard çalışıyor: http://localhost:3000${NC}"
    echo -e "${BLUE}   Kullanıcı adı: admin${NC}"
    echo -e "${BLUE}   Şifre: admin${NC}"
else
    echo -e "${YELLOW}⚠️  Grafana dashboard başlatılamadı${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Deployment tamamlandı!${NC}"
echo ""
echo -e "${BLUE}📊 Erişim Bilgileri:${NC}"
echo -e "   🌐 VeriKeşif: http://localhost:8501"
echo -e "   🗄️  MySQL: localhost:3306"
echo -e "   🤖 Ollama: http://localhost:11434"
echo -e "   📈 Prometheus: http://localhost:9090"
echo -e "   📊 Grafana: http://localhost:3000"
echo ""
echo -e "${BLUE}🔧 Yönetim Komutları:${NC}"
echo -e "   📋 Durum kontrolü: docker-compose ps"
echo -e "   📝 Logları görüntüle: docker-compose logs -f"
echo -e "   ⏹️  Durdur: docker-compose down"
echo -e "   🔄 Yeniden başlat: docker-compose restart"
echo ""
echo -e "${YELLOW}💡 İlk kullanımda Ollama modellerini yüklemeyi unutmayın:${NC}"
echo -e "   docker-compose exec ollama ollama pull llama3:latest"
echo -e "   docker-compose exec ollama ollama pull qwen2.5-coder:32b-instruct-q4_0" 