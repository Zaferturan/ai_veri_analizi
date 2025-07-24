"""
AI Helper Modülü - Ollama Destekli

Bu modül, Ollama modellerini kullanarak AI analizleri yapar.
Özellikler:
- Ollama modelleri ile metin analizi
- Özetleme, sınıflandırma, kümelendirme
- Embedding cache entegrasyonu
- Metrik izleme
"""

import logging
import json
import time
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from collections import Counter
import re
import subprocess
import requests
from pathlib import Path

# Logging konfigürasyonu
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIHelper:
    """Ollama tabanlı AI analiz yardımcısı"""
    
    # Varsayılan prompt'lar
    DEFAULT_PROMPTS = {
        "Özetleme": "Aşağıdaki metinleri analiz ederek kısa bir Türkçe özet çıkar:\n\n{texts}\n\nLütfen Türkçe olarak özetle:",
        "Sınıflandırma": "Aşağıdaki metni analiz ederek kategorisini Türkçe olarak belirle:\n\nMetin: {text}\n\nKategori (sadece Türkçe kategori adını yaz):",
        "Kümelendirme": "Aşağıdaki metinleri benzerliklerine göre Türkçe grup adlarıyla gruplandır:\n\n{texts}\n\nYanıtını şu formatta ver:\nGrup 1: [Türkçe Grup Adı] - Metinler: [numaralar]\nGrup 2: [Türkçe Grup Adı] - Metinler: [numaralar]\n...\n\nÖrnek:\nGrup 1: Şikayet Konuları - Metinler: 1, 3, 5\nGrup 2: Öneri Konuları - Metinler: 2, 4, 6",
        "Trend Analizi": "Aşağıdaki tarihli metinleri analiz ederek Türkçe trend analizi yap:\n\n{texts}\n\nTürkçe trend analizi:"
    }
    
    # Varsayılan sistem prompt'ları
    DEFAULT_SYSTEM_PROMPTS = {
        "Özetleme": "Sen bir metin analiz uzmanısın. Verilen metinleri kısa ve öz bir şekilde Türkçe olarak özetle.",
        "Sınıflandırma": "Sen bir metin sınıflandırma uzmanısın. Verilen metni uygun bir Türkçe kategoriye sınıflandır.",
        "Kümelendirme": "Sen bir metin kümelendirme uzmanısın. Verilen metinleri benzerliklerine göre Türkçe grup adlarıyla gruplandır.",
        "Trend Analizi": "Sen bir trend analiz uzmanısın. Verilen tarihli metinleri analiz ederek Türkçe trend analizi yap."
    }
    
    def __init__(self, ollama_host: str = "http://localhost:11434"):
        """
        AI Helper'ı başlat
        
        Args:
            ollama_host: Ollama sunucusunun adresi
        """
        self.ollama_host = ollama_host
        self.available_models = self._get_available_models()
        logger.info(f"Ollama istemcisi başlatıldı - {len(self.available_models)} model mevcut")
        
    def _get_available_models(self) -> List[str]:
        """Mevcut Ollama modellerini al"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
            else:
                logger.error(f"Ollama modelleri alınamadı: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Ollama bağlantı hatası: {e}")
            return []
    
    def _call_ollama(self, model: str, prompt: str, system_prompt: str = None) -> str:
        """Ollama modelini çağır"""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = requests.post(f"{self.ollama_host}/api/generate", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                logger.error(f"Ollama API hatası: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"Ollama çağrı hatası: {e}")
            return ""
    
    def summarize_texts(self, texts: List[str], model: str = "llama3:latest", custom_prompt: str = None, custom_system_prompt: str = None) -> Dict[str, Any]:
        """
        Metinleri özetle
        
        Args:
            texts: Özetlenecek metinler
            model: Kullanılacak Ollama modeli
            custom_prompt: Özel prompt (opsiyonel)
            
        Returns:
            Özetleme sonuçları
        """
        start_time = time.time()
        
        try:
            # Metinleri birleştir
            combined_text = "\n\n".join(texts[:10])  # İlk 10 metni al
            
            if custom_prompt:
                # Özel prompt kullan
                prompt = custom_prompt.replace("{texts}", combined_text)
            else:
                # Varsayılan prompt kullan
                prompt = f"""
Aşağıdaki metinleri analiz ederek kısa bir Türkçe özet çıkar:

{combined_text}

Lütfen Türkçe olarak özetle:
"""
            
            if custom_system_prompt:
                system_prompt = custom_system_prompt
            else:
                system_prompt = "Sen bir metin analiz uzmanısın. Verilen metinleri kısa ve öz bir şekilde Türkçe olarak özetle."
            
            response = self._call_ollama(model, prompt, system_prompt)
            
            # Metrikleri kaydet
            self._record_metrics("summarization", model, time.time() - start_time)
            
            return {
                'summary': response,
                'model_used': model,
                'processing_time': time.time() - start_time,
                'texts_analyzed': len(texts[:10]),
                'analysis_type': 'Özetleme'
            }
            
        except Exception as e:
            logger.error(f"Özetleme hatası: {e}")
            return {'error': str(e)}
    
    def classify_texts(self, texts: List[str], model: str = "llama3:latest", custom_prompt: str = None, custom_system_prompt: str = None) -> Dict[str, Any]:
        """
        Metinleri sınıflandır
        
        Args:
            texts: Sınıflandırılacak metinler
            model: Kullanılacak Ollama modeli
            custom_prompt: Özel prompt (opsiyonel)
            
        Returns:
            Sınıflandırma sonuçları
        """
        start_time = time.time()
        
        try:
            classifications = []
            
            for i, text in enumerate(texts[:20]):  # İlk 20 metni sınıflandır
                if custom_prompt:
                    # Özel prompt kullan
                    prompt = custom_prompt.replace("{text}", text)
                else:
                    # Varsayılan prompt kullan
                    prompt = f"""
Aşağıdaki metni analiz ederek kategorisini Türkçe olarak belirle:

Metin: {text}

Kategori (sadece Türkçe kategori adını yaz):
"""
                
                if custom_system_prompt:
                    system_prompt = custom_system_prompt
                else:
                    system_prompt = "Sen bir metin sınıflandırma uzmanısın. Verilen metni uygun bir Türkçe kategoriye sınıflandır."
                
                category = self._call_ollama(model, prompt, system_prompt).strip()
                
                classifications.append({
                    'text': text[:100] + "..." if len(text) > 100 else text,
                    'category': category,
                    'confidence': 0.8  # Ollama için sabit güven skoru
                })
            
            # Metrikleri kaydet
            self._record_metrics("classification", model, time.time() - start_time)
            
            return {
                'classifications': classifications,
                'model_used': model,
                'processing_time': time.time() - start_time,
                'texts_analyzed': len(classifications),
                'analysis_type': 'Sınıflandırma'
            }
            
        except Exception as e:
            logger.error(f"Sınıflandırma hatası: {e}")
            return {'error': str(e)}
    
    def cluster_texts(self, texts: List[str], model: str = "llama3:latest", custom_prompt: str = None, custom_system_prompt: str = None) -> Dict[str, Any]:
        """
        Metinleri kümelendir
        
        Args:
            texts: Kümelendirilecek metinler
            model: Kullanılacak Ollama modeli
            custom_prompt: Özel prompt (opsiyonel)
            
        Returns:
            Kümelendirme sonuçları
        """
        start_time = time.time()
        
        try:
            # Metinleri birleştir
            combined_text = "\n".join([f"{i+1}. {text}" for i, text in enumerate(texts[:15])])
            
            if custom_prompt:
                # Özel prompt kullan
                prompt = custom_prompt.replace("{texts}", combined_text)
            else:
                # Varsayılan prompt kullan
                prompt = f"""
Aşağıdaki metinleri benzerliklerine göre Türkçe grup adlarıyla gruplandır:

{combined_text}

Yanıtını şu formatta ver:
Grup 1: [Türkçe Grup Adı] - Metinler: [numaralar]
Grup 2: [Türkçe Grup Adı] - Metinler: [numaralar]
...

Örnek:
Grup 1: Şikayet Konuları - Metinler: 1, 3, 5
Grup 2: Öneri Konuları - Metinler: 2, 4, 6
"""
            
            if custom_system_prompt:
                system_prompt = custom_system_prompt
            else:
                system_prompt = "Sen bir metin kümelendirme uzmanısın. Verilen metinleri benzerliklerine göre Türkçe grup adlarıyla gruplandır. Yanıtını JSON formatında ver."
            
            response = self._call_ollama(model, prompt, system_prompt)
            
            # Yanıtı parse et
            clusters = self._parse_clustering_response(response, texts[:15])
            
            # Metrikleri kaydet
            self._record_metrics("clustering", model, time.time() - start_time)
            
            return {
                'clusters': clusters,
                'raw_response': response,
                'model_used': model,
                'processing_time': time.time() - start_time,
                'texts_analyzed': len(texts[:15]),
                'analysis_type': 'Kümelendirme'
            }
            
        except Exception as e:
            logger.error(f"Kümelendirme hatası: {e}")
            return {'error': str(e)}
    
    def analyze_trends(self, texts: List[str], dates: List[str], model: str = "llama3:latest", custom_prompt: str = None, custom_system_prompt: str = None) -> Dict[str, Any]:
        """
        Trend analizi yap
        
        Args:
            texts: Analiz edilecek metinler
            dates: Tarihler
            model: Kullanılacak Ollama modeli
            custom_prompt: Özel prompt (opsiyonel)
            
        Returns:
            Trend analizi sonuçları
        """
        start_time = time.time()
        
        try:
            # Metin ve tarihleri birleştir
            combined_data = "\n".join([f"{date}: {text}" for date, text in zip(dates[:10], texts[:10])])
            
            if custom_prompt:
                # Özel prompt kullan
                prompt = custom_prompt.replace("{texts}", combined_data)
            else:
                # Varsayılan prompt kullan
                prompt = f"""
Aşağıdaki tarihli metinleri analiz ederek Türkçe trend analizi yap:

{combined_data}

Türkçe trend analizi:
"""
            
            if custom_system_prompt:
                system_prompt = custom_system_prompt
            else:
                system_prompt = "Sen bir trend analiz uzmanısın. Verilen tarihli metinleri analiz ederek Türkçe trend analizi yap."
            
            response = self._call_ollama(model, prompt, system_prompt)
            
            # Metrikleri kaydet
            self._record_metrics("trend_analysis", model, time.time() - start_time)
            
            return {
                'trends': response,
                'model_used': model,
                'processing_time': time.time() - start_time,
                'texts_analyzed': len(texts[:10]),
                'analysis_type': 'Trend Analizi'
            }
            
        except Exception as e:
            logger.error(f"Trend analizi hatası: {e}")
            return {'error': str(e)}
    
    def _parse_clustering_response(self, response: str, texts: List[str]) -> List[Dict[str, Any]]:
        """Kümelendirme yanıtını parse et"""
        try:
            # JSON formatında yanıt gelirse
            import json
            data = json.loads(response)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'clusters' in data:
                return data['clusters']
        except:
            pass
        
        # JSON parse edilemezse, metin formatını parse et
        clusters = []
        lines = response.strip().split('\n')
        current_cluster = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Grup başlığı ara (Grup 1:, Küme 1:, vb.)
            if any(keyword in line.lower() for keyword in ['grup', 'küme', 'cluster', 'group']):
                # Önceki kümeyi kaydet
                if current_cluster:
                    clusters.append(current_cluster)
                
                # Yeni küme başlat
                cluster_name = line.split(':')[0].strip()
                current_cluster = {
                    'name': cluster_name,
                    'texts': [],
                    'text_indices': []
                }
                
                # Metin numaralarını ara
                import re
                numbers = re.findall(r'\d+', line)
                for num in numbers:
                    idx = int(num) - 1  # 1-based to 0-based
                    if 0 <= idx < len(texts):
                        current_cluster['text_indices'].append(idx)
                        current_cluster['texts'].append(texts[idx])
        
        # Son kümeyi ekle
        if current_cluster:
            clusters.append(current_cluster)
        
        # Eğer hiç küme bulunamazsa, her metni ayrı küme yap
        if not clusters:
            for i, text in enumerate(texts):
                clusters.append({
                    'name': f'Küme {i+1}',
                    'texts': [text],
                    'text_indices': [i]
                })
        
        return clusters
    
    def _record_metrics(self, operation: str, model: str, duration: float):
        """Metrikleri kaydet"""
        try:
            from metrics import record_ai_call
            record_ai_call(operation, model, duration, 0)  # Token sayısı Ollama için 0
        except ImportError:
            logger.warning("Metrics modülü bulunamadı")
    
    def get_available_models(self) -> List[str]:
        """Mevcut modelleri döndür"""
        return self.available_models
    
    def get_default_prompt(self, action: str) -> str:
        """Varsayılan prompt'u al"""
        return self.DEFAULT_PROMPTS.get(action, "")
    
    def get_default_system_prompt(self, action: str) -> str:
        """Varsayılan sistem prompt'u al"""
        return self.DEFAULT_SYSTEM_PROMPTS.get(action, "")
    
    def test_connection(self) -> bool:
        """Ollama bağlantısını test et"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags")
            return response.status_code == 200
        except:
            return False

def main():
    """CLI arayüzü"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ollama AI Helper")
    parser.add_argument("--model", default="llama3:latest", help="Kullanılacak model")
    parser.add_argument("--operation", choices=["summarize", "classify", "cluster", "trends"], 
                       required=True, help="Yapılacak işlem")
    parser.add_argument("--input", required=True, help="Giriş dosyası")
    parser.add_argument("--output", help="Çıkış dosyası")
    
    args = parser.parse_args()
    
    # AI Helper'ı başlat
    ai_helper = AIHelper()
    
    # Metinleri oku
    with open(args.input, 'r', encoding='utf-8') as f:
        texts = [line.strip() for line in f if line.strip()]
    
    # İşlemi gerçekleştir
    if args.operation == "summarize":
        result = ai_helper.summarize_texts(texts, args.model)
    elif args.operation == "classify":
        result = ai_helper.classify_texts(texts, args.model)
    elif args.operation == "cluster":
        result = ai_helper.cluster_texts(texts, args.model)
    elif args.operation == "trends":
        dates = [f"2024-{i+1:02d}-01" for i in range(len(texts))]
        result = ai_helper.analyze_trends(texts, dates, args.model)
    
    # Sonucu yazdır
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main() 