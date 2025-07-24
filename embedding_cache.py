"""
💾 Embedding Cache Sistemi

Bu modül metin embed işlemlerinde tekrar eden çağrıları engellemek için 
önbellekleme sistemi sağlar. Aynı metin daha önce embed edildiyse 
tekrar API çağrısı yapılmaz.
"""

import sqlite3
import numpy as np
import json
import hashlib
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import logging
from sentence_transformers import SentenceTransformer
import argparse

# Logging konfigürasyonu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmbeddingCache:
    """
    Metin embedding'leri için önbellekleme sistemi.
    SQLite veritabanı kullanarak embedding'leri saklar.
    """
    
    def __init__(self, db_path: str = "embedding_cache.db", model_name: str = "all-MiniLM-L6-v2"):
        """
        EmbeddingCache başlatıcı
        
        Args:
            db_path: SQLite veritabanı dosya yolu
            model_name: Sentence transformer model adı
        """
        self.db_path = db_path
        self.model_name = model_name
        self.model = None
        self._init_database()
        self._load_model()
    
    def _init_database(self):
        """Veritabanını başlat ve tabloları oluştur"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Embedding cache tablosu
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS embeddings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        text_hash TEXT UNIQUE NOT NULL,
                        text_content TEXT NOT NULL,
                        embedding_vector TEXT NOT NULL,
                        model_name TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 1
                    )
                """)
                
                # Cache istatistikleri tablosu
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cache_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        total_embeddings INTEGER DEFAULT 0,
                        cache_hits INTEGER DEFAULT 0,
                        cache_misses INTEGER DEFAULT 0,
                        total_requests INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # İlk istatistik kaydını oluştur
                cursor.execute("""
                    INSERT OR IGNORE INTO cache_stats (id, total_embeddings, cache_hits, cache_misses, total_requests)
                    VALUES (1, 0, 0, 0, 0)
                """)
                
                conn.commit()
                logger.info(f"Veritabanı başlatıldı: {self.db_path}")
                
        except Exception as e:
            logger.error(f"Veritabanı başlatma hatası: {e}")
            raise
    
    def _load_model(self):
        """Sentence transformer modelini yükle"""
        try:
            logger.info(f"Model yükleniyor: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Model başarıyla yüklendi")
        except Exception as e:
            logger.error(f"Model yükleme hatası: {e}")
            raise
    
    def _hash_text(self, text: str) -> str:
        """Metni hash'le"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _serialize_embedding(self, embedding: np.ndarray) -> str:
        """NumPy array'i JSON string'e çevir"""
        return json.dumps(embedding.tolist())
    
    def _deserialize_embedding(self, embedding_str: str) -> np.ndarray:
        """JSON string'i NumPy array'e çevir"""
        return np.array(json.loads(embedding_str))
    
    def get_embedding(self, text: str) -> np.ndarray:
        """
        Metin için embedding al. Cache'de varsa oradan, yoksa model ile oluştur.
        
        Args:
            text: Embed edilecek metin
            
        Returns:
            Embedding vector (numpy array)
        """
        if not text or not text.strip():
            raise ValueError("Boş metin embed edilemez")
        
        text = text.strip()
        text_hash = self._hash_text(text)
        
        # Cache'de ara
        cached_embedding = self._get_from_cache(text_hash)
        if cached_embedding is not None:
            self._update_cache_stats(hit=True)
            logger.debug(f"Cache hit: {text[:50]}...")
            return cached_embedding
        
        # Cache'de yok, model ile oluştur
        logger.debug(f"Cache miss: {text[:50]}...")
        embedding = self._create_embedding(text)
        self._save_to_cache(text_hash, text, embedding)
        self._update_cache_stats(hit=False)
        
        return embedding
    
    def _get_from_cache(self, text_hash: str) -> Optional[np.ndarray]:
        """Cache'den embedding al"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT embedding_vector, last_accessed, access_count 
                    FROM embeddings 
                    WHERE text_hash = ?
                """, (text_hash,))
                
                result = cursor.fetchone()
                if result:
                    embedding_str, last_accessed, access_count = result
                    
                    # Erişim sayısını ve zamanını güncelle
                    cursor.execute("""
                        UPDATE embeddings 
                        SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                        WHERE text_hash = ?
                    """, (text_hash,))
                    
                    conn.commit()
                    return self._deserialize_embedding(embedding_str)
                
                return None
                
        except Exception as e:
            logger.error(f"Cache okuma hatası: {e}")
            return None
    
    def _create_embedding(self, text: str) -> np.ndarray:
        """Model ile yeni embedding oluştur"""
        try:
            embedding = self.model.encode(text)
            return embedding
        except Exception as e:
            logger.error(f"Embedding oluşturma hatası: {e}")
            raise
    
    def _save_to_cache(self, text_hash: str, text: str, embedding: np.ndarray):
        """Embedding'i cache'e kaydet"""
        try:
            embedding_str = self._serialize_embedding(embedding)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO embeddings (text_hash, text_content, embedding_vector, model_name)
                    VALUES (?, ?, ?, ?)
                """, (text_hash, text, embedding_str, self.model_name))
                
                conn.commit()
                logger.debug(f"Embedding cache'e kaydedildi: {text[:50]}...")
                
        except sqlite3.IntegrityError:
            # Hash zaten var, güncelleme yapma
            logger.debug("Embedding zaten cache'de mevcut")
        except Exception as e:
            logger.error(f"Cache kaydetme hatası: {e}")
    
    def _update_cache_stats(self, hit: bool):
        """Cache istatistiklerini güncelle"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if hit:
                    cursor.execute("""
                        UPDATE cache_stats 
                        SET cache_hits = cache_hits + 1, 
                            total_requests = total_requests + 1,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE id = 1
                    """)
                else:
                    cursor.execute("""
                        UPDATE cache_stats 
                        SET cache_misses = cache_misses + 1, 
                            total_requests = total_requests + 1,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE id = 1
                    """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"İstatistik güncelleme hatası: {e}")
    
    def get_cache_size(self) -> int:
        """Cache'deki toplam kayıt sayısını döndür"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM embeddings")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Cache boyutu alma hatası: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Cache istatistiklerini döndür"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT total_embeddings, cache_hits, cache_misses, total_requests, last_updated
                    FROM cache_stats WHERE id = 1
                """)
                
                result = cursor.fetchone()
                if result:
                    total_embeddings, hits, misses, total_requests, last_updated = result
                    
                    hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
                    
                    return {
                        "total_embeddings": total_embeddings,
                        "cache_hits": hits,
                        "cache_misses": misses,
                        "total_requests": total_requests,
                        "hit_rate": round(hit_rate, 2),
                        "last_updated": last_updated
                    }
                
                return {}
                
        except Exception as e:
            logger.error(f"İstatistik alma hatası: {e}")
            return {}
    
    def clear_cache(self):
        """Tüm cache'i temizle"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM embeddings")
                cursor.execute("""
                    UPDATE cache_stats 
                    SET total_embeddings = 0, cache_hits = 0, cache_misses = 0, total_requests = 0
                    WHERE id = 1
                """)
                conn.commit()
                logger.info("Cache temizlendi")
                
        except Exception as e:
            logger.error(f"Cache temizleme hatası: {e}")
    
    def get_oldest_embeddings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """En eski embedding'leri listele"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT text_content, created_at, last_accessed, access_count
                    FROM embeddings
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (limit,))
                
                results = []
                for row in cursor.fetchall():
                    text, created_at, last_accessed, access_count = row
                    results.append({
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "created_at": created_at,
                        "last_accessed": last_accessed,
                        "access_count": access_count
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Eski embedding'leri alma hatası: {e}")
            return []
    
    def cleanup_old_embeddings(self, days: int = 30):
        """Belirtilen günden eski embedding'leri sil"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM embeddings 
                    WHERE created_at < ?
                """, (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                logger.info(f"{deleted_count} eski embedding silindi")
                
        except Exception as e:
            logger.error(f"Eski embedding temizleme hatası: {e}")


def main():
    """CLI arayüzü"""
    parser = argparse.ArgumentParser(description="Embedding Cache Sistemi")
    parser.add_argument("--text", type=str, help="Embed edilecek metin")
    parser.add_argument("--file", type=str, help="Metin dosyası yolu")
    parser.add_argument("--stats", action="store_true", help="Cache istatistiklerini göster")
    parser.add_argument("--clear", action="store_true", help="Cache'i temizle")
    parser.add_argument("--list", action="store_true", help="En eski embedding'leri listele")
    parser.add_argument("--cleanup", type=int, help="Belirtilen günden eski embedding'leri sil")
    parser.add_argument("--db", type=str, default="embedding_cache.db", help="Veritabanı dosya yolu")
    parser.add_argument("--model", type=str, default="all-MiniLM-L6-v2", help="Model adı")
    
    args = parser.parse_args()
    
    try:
        cache = EmbeddingCache(db_path=args.db, model_name=args.model)
        
        if args.stats:
            stats = cache.get_cache_stats()
            print("📊 Cache İstatistikleri:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        elif args.clear:
            cache.clear_cache()
            print("🗑️ Cache temizlendi")
        
        elif args.list:
            embeddings = cache.get_oldest_embeddings()
            print("📋 En Eski Embedding'ler:")
            for i, emb in enumerate(embeddings, 1):
                print(f"  {i}. {emb['text']}")
                print(f"     Oluşturulma: {emb['created_at']}")
                print(f"     Son Erişim: {emb['last_accessed']}")
                print(f"     Erişim Sayısı: {emb['access_count']}")
                print()
        
        elif args.cleanup:
            cache.cleanup_old_embeddings(args.cleanup)
            print(f"🧹 {args.cleanup} günden eski embedding'ler temizlendi")
        
        elif args.text:
            embedding = cache.get_embedding(args.text)
            print(f"✅ Embedding oluşturuldu (boyut: {embedding.shape})")
            print(f"📝 Metin: {args.text[:100]}...")
        
        elif args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
            embedding = cache.get_embedding(text)
            print(f"✅ Dosya embedding'i oluşturuldu (boyut: {embedding.shape})")
            print(f"📁 Dosya: {args.file}")
        
        else:
            # İnteraktif mod
            print("🤖 Embedding Cache Sistemi")
            print("Çıkmak için 'quit' yazın")
            
            while True:
                text = input("\n📝 Metin girin: ").strip()
                if text.lower() in ['quit', 'exit', 'q']:
                    break
                
                if text:
                    try:
                        embedding = cache.get_embedding(text)
                        print(f"✅ Embedding boyutu: {embedding.shape}")
                        print(f"📊 Cache boyutu: {cache.get_cache_size()}")
                    except Exception as e:
                        print(f"❌ Hata: {e}")
    
    except Exception as e:
        logger.error(f"Ana program hatası: {e}")
        print(f"❌ Hata: {e}")


if __name__ == "__main__":
    main() 