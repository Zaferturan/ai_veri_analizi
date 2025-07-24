#!/usr/bin/env python3
"""
API Anahtarlarını Test Etme Scripti
"""
import os
from dotenv import load_dotenv
import openai
import google.generativeai as genai

# .env dosyasını yükle
load_dotenv('.env')

def test_openai():
    """OpenAI API anahtarını test et"""
    api_key = os.getenv('OPENAI_API_KEY')
    print(f"OpenAI API Key (ilk 10 karakter): {api_key[:10]}...")
    
    if not api_key:
        print("❌ OpenAI API anahtarı bulunamadı")
        return False
    
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Merhaba"}],
            max_tokens=5
        )
        print("✅ OpenAI API anahtarı geçerli")
        return True
    except Exception as e:
        if "quota" in str(e).lower() or "429" in str(e):
            print("⚠️ OpenAI API anahtarı geçerli ama quota aşıldı")
            return True  # Anahtar geçerli, sadece limit aşıldı
        else:
            print(f"❌ OpenAI API anahtarı geçersiz: {e}")
            return False

def test_gemini():
    """Gemini API anahtarını test et"""
    api_key = os.getenv('GEMINI_API_KEY')
    print(f"Gemini API Key (ilk 10 karakter): {api_key[:10]}...")
    
    if not api_key:
        print("❌ Gemini API anahtarı bulunamadı")
        return False
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content("Merhaba")
        print("✅ Gemini API anahtarı geçerli")
        return True
    except Exception as e:
        if "quota" in str(e).lower() or "429" in str(e):
            print("⚠️ Gemini API anahtarı geçerli ama quota aşıldı")
            return True  # Anahtar geçerli, sadece limit aşıldı
        else:
            print(f"❌ Gemini API anahtarı geçersiz: {e}")
            return False

if __name__ == "__main__":
    print("🔑 API Anahtarlarını Test Ediyorum...")
    print("=" * 50)
    
    openai_ok = test_openai()
    print()
    gemini_ok = test_gemini()
    
    print("=" * 50)
    if openai_ok and gemini_ok:
        print("🎉 Tüm API anahtarları geçerli!")
    else:
        print("⚠️  Bazı API anahtarları geçersiz. Lütfen kontrol edin.") 