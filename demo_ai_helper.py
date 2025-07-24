#!/usr/bin/env python3
"""
AI Helper Demo Script
AI destekli analiz sisteminin kullanımını gösteren demo script
"""

import json
from ai_helper import AIHelper, load_texts_from_file

def demo_ai_helper():
    """AI Helper'ın temel özelliklerini göster"""
    
    print("🤖 AI Destekli Analiz Sistemi Demo")
    print("=" * 50)
    
    # AI Helper başlat
    ai_helper = AIHelper()
    
    # Örnek metinler
    sample_texts = [
        "Kullanıcı arayüzü çok yavaş ve kullanışsız. Performans iyileştirmesi gerekiyor.",
        "Yeni özellik önerisi: Mobil uygulama geliştirilmeli ve push notification eklenmeli.",
        "Sistem sürekli çöküyor ve veri kaybı yaşanıyor. Acil düzeltme gerekiyor.",
        "Raporlama modülü çok kullanışlı. Grafik ve istatistikler harika görünüyor.",
        "Güvenlik açığı tespit edildi. Kullanıcı verileri korunmuyor."
    ]
    
    print(f"\n📝 Örnek Metinler ({len(sample_texts)} adet):")
    for i, text in enumerate(sample_texts, 1):
        print(f"{i}. {text[:60]}...")
    
    # 1. Özetleme Demo
    print("\n" + "=" * 50)
    print("📋 1. Metin Özetleme Demo")
    print("=" * 50)
    
    try:
        summary_result = ai_helper.summarize_texts(sample_texts, model="openai", max_length=300)
        if "error" in summary_result:
            print(f"❌ Özetleme hatası: {summary_result['error']}")
            print("💡 API anahtarı gerekli: OPENAI_API_KEY veya GEMINI_API_KEY")
        else:
            print(f"✅ Özet başarılı!")
            print(f"📊 Model: {summary_result['model']}")
            print(f"📏 Uzunluk: {summary_result['length']} karakter")
            print(f"📝 Özet: {summary_result['summary']}")
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
    
    # 2. Kümeleme Demo
    print("\n" + "=" * 50)
    print("🏷️ 2. Metin Kümeleme Demo")
    print("=" * 50)
    
    try:
        cluster_result = ai_helper.cluster_texts(sample_texts, model="openai", n_clusters=3)
        if "error" in cluster_result:
            print(f"❌ Kümeleme hatası: {cluster_result['error']}")
        else:
            print(f"✅ Kümeleme başarılı!")
            print(f"📊 Model: {cluster_result['model']}")
            print(f"🎯 Küme sayısı: {cluster_result['n_clusters']}")
            for i, cluster in enumerate(cluster_result['clusters'], 1):
                print(f"\n📦 Küme {i}: {cluster['name']}")
                print(f"   📄 Metinler: {cluster['text_indices']}")
                print(f"   📝 Açıklama: {cluster['description']}")
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
    
    # 3. Sınıflandırma Demo
    print("\n" + "=" * 50)
    print("🏷️ 3. Metin Sınıflandırma Demo")
    print("=" * 50)
    
    categories = ["Şikayet", "Öneri", "Pozitif", "Teknik"]
    
    try:
        classify_result = ai_helper.classify_texts(sample_texts, model="openai", categories=categories)
        if "error" in classify_result:
            print(f"❌ Sınıflandırma hatası: {classify_result['error']}")
        else:
            print(f"✅ Sınıflandırma başarılı!")
            print(f"📊 Model: {classify_result['model']}")
            print(f"🏷️ Kategoriler: {', '.join(classify_result['categories'])}")
            for item in classify_result['classifications']:
                text_idx = item['text_index']
                category = item['category']
                confidence = item.get('confidence', 'N/A')
                reason = item.get('reason', 'N/A')
                print(f"\n📄 Metin {text_idx}: {category} (Güven: {confidence})")
                print(f"   💭 Neden: {reason}")
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
    
    # 4. Trend Analizi Demo
    print("\n" + "=" * 50)
    print("📈 4. Trend Analizi Demo")
    print("=" * 50)
    
    dates = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
    
    try:
        trend_result = ai_helper.analyze_trends(sample_texts, dates, model="openai")
        if "error" in trend_result:
            print(f"❌ Trend analizi hatası: {trend_result['error']}")
        else:
            print(f"✅ Trend analizi başarılı!")
            print(f"📊 Model: {trend_result['model']}")
            print(f"📅 Tarih aralığı: {trend_result['date_range']}")
            
            if trend_result.get('trends'):
                print(f"\n📈 Tespit Edilen Trendler:")
                for trend in trend_result['trends']:
                    print(f"   🔍 {trend['trend_type']}: {trend['description']}")
                    print(f"      📅 Dönem: {trend['period']}")
                    print(f"      🎯 Güven: {trend['confidence']}")
            
            if trend_result.get('key_insights'):
                print(f"\n💡 Önemli Bulgular:")
                for insight in trend_result['key_insights']:
                    print(f"   • {insight}")
            
            if trend_result.get('recommendations'):
                print(f"\n💡 Öneriler:")
                for rec in trend_result['recommendations']:
                    print(f"   • {rec}")
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
    
    # 5. Dosya İşlemleri Demo
    print("\n" + "=" * 50)
    print("📁 5. Dosya İşlemleri Demo")
    print("=" * 50)
    
    # Örnek dosya oluştur
    demo_file = "demo_texts.txt"
    with open(demo_file, 'w', encoding='utf-8') as f:
        for text in sample_texts:
            f.write(text + '\n')
    
    try:
        loaded_texts = load_texts_from_file(demo_file)
        print(f"✅ Dosyadan {len(loaded_texts)} metin yüklendi")
        
        # Dosyadan yüklenen metinlerle özetleme
        file_summary = ai_helper.summarize_texts(loaded_texts[:3], model="openai", max_length=200)
        if "error" not in file_summary:
            print(f"📝 Dosya özeti: {file_summary['summary'][:100]}...")
        
        # Sonuçları dosyaya kaydet
        demo_result = {
            "demo_type": "AI Helper Demo",
            "total_texts": len(sample_texts),
            "categories": categories,
            "timestamp": "2024-07-01T12:00:00"
        }
        
        output_file = ai_helper.export_analysis(demo_result, "demo_result.json")
        if output_file:
            print(f"💾 Demo sonuçları kaydedildi: {output_file}")
        
    except Exception as e:
        print(f"❌ Dosya işlemi hatası: {e}")
    finally:
        # Demo dosyasını temizle
        import os
        if os.path.exists(demo_file):
            os.remove(demo_file)
    
    print("\n" + "=" * 50)
    print("🎉 Demo Tamamlandı!")
    print("=" * 50)
    
    print("\n💡 Kullanım İpuçları:")
    print("• API anahtarlarını .env dosyasında saklayın")
    print("• OPENAI_API_KEY veya GEMINI_API_KEY gerekli")
    print("• Embedding cache ile performansı artırın")
    print("• Sonuçları JSON formatında kaydedin")
    
    print("\n📚 Daha fazla bilgi için:")
    print("• python ai_helper.py --help")
    print("• README.md dosyasını inceleyin")
    print("• test_ai_helper.py testlerini çalıştırın")

if __name__ == "__main__":
    demo_ai_helper() 