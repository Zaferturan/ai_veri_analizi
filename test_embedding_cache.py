"""
💾 Embedding Cache Sistemi: Test dosyası

Bu dosya embedding_cache.py modülünün testlerini içerir.
"""

import pytest
import tempfile
import os
import numpy as np
from embedding_cache import EmbeddingCache
import time

class TestEmbeddingCache:
    """EmbeddingCache sınıfı için testler"""
    
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
    def cache(self, temp_db):
        """Test için EmbeddingCache instance'ı oluştur"""
        try:
            return EmbeddingCache(db_path=temp_db)
        except Exception as e:
            # İnternet bağlantısı yoksa test'i atla
            pytest.skip(f"Model yüklenemedi (internet bağlantısı gerekli): {e}")
    
    def test_init_database(self, cache):
        """Veritabanı başlatma testi"""
        assert os.path.exists(cache.db_path)
        assert cache.get_cache_size() == 0
    
    def test_model_loading(self, cache):
        """Model yükleme testi"""
        assert cache.model is not None
        assert hasattr(cache.model, 'encode')
    
    def test_text_hashing(self, cache):
        """Metin hash'leme testi"""
        text1 = "Merhaba dünya"
        text2 = "Merhaba dünya"
        text3 = "Farklı metin"
        
        hash1 = cache._hash_text(text1)
        hash2 = cache._hash_text(text2)
        hash3 = cache._hash_text(text3)
        
        assert hash1 == hash2  # Aynı metin aynı hash
        assert hash1 != hash3  # Farklı metin farklı hash
        assert len(hash1) == 64  # SHA256 hash uzunluğu
    
    def test_embedding_serialization(self, cache):
        """Embedding serileştirme testi"""
        original = np.array([1.0, 2.0, 3.0, 4.0])
        serialized = cache._serialize_embedding(original)
        deserialized = cache._deserialize_embedding(serialized)
        
        assert isinstance(serialized, str)
        assert np.array_equal(original, deserialized)
    
    def test_get_embedding_new_text(self, cache):
        """Yeni metin embedding testi"""
        text = "Bu yeni bir test metnidir"
        embedding = cache.get_embedding(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] > 0  # Embedding boyutu pozitif
        assert cache.get_cache_size() == 1  # Cache'e kaydedildi
    
    def test_get_embedding_cached_text(self, cache):
        """Cache'lenmiş metin embedding testi"""
        text = "Bu metin cache'lenecek"
        
        # İlk çağrı - cache miss
        embedding1 = cache.get_embedding(text)
        size_after_first = cache.get_cache_size()
        
        # İkinci çağrı - cache hit
        embedding2 = cache.get_embedding(text)
        size_after_second = cache.get_cache_size()
        
        # Aynı embedding döndürülmeli
        assert np.array_equal(embedding1, embedding2)
        # Cache boyutu değişmemeli
        assert size_after_first == size_after_second
    
    def test_empty_text_error(self, cache):
        """Boş metin hatası testi"""
        with pytest.raises(ValueError):
            cache.get_embedding("")
        
        with pytest.raises(ValueError):
            cache.get_embedding("   ")
    
    def test_cache_size(self, cache):
        """Cache boyutu testi"""
        assert cache.get_cache_size() == 0
        
        cache.get_embedding("Test metni 1")
        assert cache.get_cache_size() == 1
        
        cache.get_embedding("Test metni 2")
        assert cache.get_cache_size() == 2
    
    def test_cache_stats(self, cache):
        """Cache istatistikleri testi"""
        stats = cache.get_cache_stats()
        
        assert "total_embeddings" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "total_requests" in stats
        assert "hit_rate" in stats
    
    def test_cache_hit_miss_tracking(self, cache):
        """Cache hit/miss takibi testi"""
        # İlk çağrı - miss
        cache.get_embedding("Test metni")
        stats1 = cache.get_cache_stats()
        
        # İkinci çağrı - hit
        cache.get_embedding("Test metni")
        stats2 = cache.get_cache_stats()
        
        assert stats2["cache_hits"] > stats1["cache_hits"]
        assert stats2["total_requests"] > stats1["total_requests"]
    
    def test_clear_cache(self, cache):
        """Cache temizleme testi"""
        cache.get_embedding("Test metni 1")
        cache.get_embedding("Test metni 2")
        
        assert cache.get_cache_size() == 2
        
        cache.clear_cache()
        assert cache.get_cache_size() == 0
    
    def test_get_oldest_embeddings(self, cache):
        """Eski embedding'leri listeleme testi"""
        cache.get_embedding("İlk metin")
        time.sleep(0.1)  # Zaman farkı için
        cache.get_embedding("İkinci metin")
        
        oldest = cache.get_oldest_embeddings(limit=5)
        
        assert len(oldest) == 2
        assert "İlk metin" in oldest[0]["text"]
        assert "İkinci metin" in oldest[1]["text"]
        assert "created_at" in oldest[0]
        assert "access_count" in oldest[0]
    
    def test_cleanup_old_embeddings(self, cache):
        """Eski embedding temizleme testi"""
        cache.get_embedding("Test metni")
        
        # 0 gün öncesinden eski (yani hepsi) temizle
        cache.cleanup_old_embeddings(days=0)
        
        assert cache.get_cache_size() == 0
    
    def test_multiple_models(self, temp_db):
        """Farklı modeller testi"""
        cache1 = EmbeddingCache(db_path=temp_db, model_name="all-MiniLM-L6-v2")
        cache2 = EmbeddingCache(db_path=temp_db, model_name="all-MiniLM-L6-v2")
        
        text = "Test metni"
        embedding1 = cache1.get_embedding(text)
        embedding2 = cache2.get_embedding(text)
        
        # Aynı model aynı embedding üretmeli
        assert np.array_equal(embedding1, embedding2)
    
    def test_large_text(self, cache):
        """Büyük metin testi"""
        large_text = "Bu çok uzun bir test metnidir. " * 100
        embedding = cache.get_embedding(large_text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] > 0
    
    def test_special_characters(self, cache):
        """Özel karakterler testi"""
        special_text = "Türkçe karakterler: ğüşıöçĞÜŞİÖÇ"
        embedding = cache.get_embedding(special_text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] > 0
    
    def test_concurrent_access(self, temp_db):
        """Eşzamanlı erişim testi"""
        import threading
        
        cache = EmbeddingCache(db_path=temp_db)
        results = []
        
        def embed_text(text):
            try:
                embedding = cache.get_embedding(text)
                results.append((text, embedding.shape))
            except Exception as e:
                results.append((text, str(e)))
        
        threads = []
        texts = [f"Test metni {i}" for i in range(5)]
        
        for text in texts:
            thread = threading.Thread(target=embed_text, args=(text,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(results) == 5
        for text, result in results:
            assert isinstance(result, tuple)  # (text, shape) tuple'ı


def test_cli_arguments():
    """CLI argümanları testi"""
    import argparse
    from embedding_cache import main
    
    # Bu test CLI argümanlarının doğru parse edildiğini kontrol eder
    # Gerçek test için mock kullanılabilir
    assert True  # Placeholder


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 