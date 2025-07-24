#!/usr/bin/env python3
"""
Metrics Modülü Test Dosyası

Bu dosya, metrics.py modülünün tüm fonksiyonlarını test eder.
"""

import pytest
import time
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Test edilecek modülü import et
from metrics import (
    MetricsCollector, 
    get_metrics_collector,
    log_ai_call,
    track_ai_call,
    start_metrics_server,
    get_metrics_summary,
    export_metrics,
    reset_metrics
)

class TestMetricsCollector:
    """MetricsCollector sınıfı testleri"""
    
    @pytest.fixture
    def collector(self):
        """Test için MetricsCollector instance'ı oluştur"""
        # Prometheus client'ı mock'la ve PROMETHEUS_AVAILABLE'ı False yap
        with patch.dict('sys.modules', {
            'prometheus_client': Mock()
        }), patch('metrics.PROMETHEUS_AVAILABLE', False):
            collector = MetricsCollector()
            return collector
    
    def test_init(self, collector):
        """MetricsCollector başlatma testi"""
        # Prometheus client mock'landığı için metrics_initialized False olacak
        assert collector.metrics_initialized is False
        assert collector.metrics_server_running is False
        assert collector.metrics_server_port == 9000
        assert collector.stats['total_calls'] == 0
        assert collector.stats['total_tokens'] == 0
        assert collector.stats['total_errors'] == 0
    
    def test_init_metrics_without_prometheus(self, collector):
        """Prometheus olmadan metrik başlatma testi"""
        # Prometheus client'ı mock'la
        with patch('metrics.PROMETHEUS_AVAILABLE', False):
            collector.init_metrics()
            assert collector.metrics_initialized is False
    
    def test_init_metrics_with_prometheus(self):
        """Prometheus ile metrik başlatma testi"""
        # Prometheus client'ı mock'la
        mock_counter = Mock()
        mock_histogram = Mock()
        mock_gauge = Mock()
        
        with patch('metrics.PROMETHEUS_AVAILABLE', True), \
             patch('metrics.Counter', return_value=mock_counter), \
             patch('metrics.Histogram', return_value=mock_histogram), \
             patch('metrics.Gauge', return_value=mock_gauge):
            
            collector = MetricsCollector()
            assert collector.metrics_initialized is True
            assert collector.ai_call_counter == mock_counter
            assert collector.ai_token_counter == mock_counter
            assert collector.ai_latency_histogram == mock_histogram
            assert collector.ai_active_requests == mock_gauge
            assert collector.ai_error_counter == mock_counter
    
    def test_log_ai_call(self, collector):
        """AI çağrı loglama testi"""
        # İlk çağrı
        collector.log_ai_call("openai", "summarize", tokens_used=100, latency=1.5)
        
        assert collector.stats['total_calls'] == 1
        assert collector.stats['total_tokens'] == 100
        assert collector.stats['total_errors'] == 0
        assert "openai" in collector.stats['model_stats']
        assert collector.stats['model_stats']['openai']['calls'] == 1
        assert collector.stats['model_stats']['openai']['tokens'] == 100
        assert collector.stats['model_stats']['openai']['total_latency'] == 1.5
        
        # İkinci çağrı (aynı model)
        collector.log_ai_call("openai", "classify", tokens_used=50, latency=0.8)
        
        assert collector.stats['total_calls'] == 2
        assert collector.stats['total_tokens'] == 150
        assert collector.stats['model_stats']['openai']['calls'] == 2
        assert collector.stats['model_stats']['openai']['tokens'] == 150
        assert collector.stats['model_stats']['openai']['total_latency'] == 2.3
        
        # Farklı model
        collector.log_ai_call("gemini", "summarize", tokens_used=75, latency=1.2)
        
        assert collector.stats['total_calls'] == 3
        assert collector.stats['total_tokens'] == 225
        assert "gemini" in collector.stats['model_stats']
        assert collector.stats['model_stats']['gemini']['calls'] == 1
        assert collector.stats['model_stats']['gemini']['tokens'] == 75
    
    def test_log_ai_call_with_error(self, collector):
        """Hata ile AI çağrı loglama testi"""
        collector.log_ai_call("openai", "summarize", tokens_used=50, latency=0.5, error_type="APIError")
        
        assert collector.stats['total_calls'] == 1
        assert collector.stats['total_tokens'] == 50
        assert collector.stats['total_errors'] == 1
        assert collector.stats['model_stats']['openai']['errors'] == 1
    
    def test_track_ai_call_success(self, collector):
        """Başarılı AI çağrı izleme testi"""
        with collector.track_ai_call("openai", "summarize"):
            time.sleep(0.1)  # Kısa bir işlem simülasyonu
        
        assert collector.stats['total_calls'] == 1
        assert collector.stats['total_tokens'] == 0
        assert collector.stats['total_errors'] == 0
        assert collector.stats['model_stats']['openai']['calls'] == 1
        assert collector.stats['model_stats']['openai']['total_latency'] > 0
    
    def test_track_ai_call_with_exception(self, collector):
        """Hata ile AI çağrı izleme testi"""
        with pytest.raises(ValueError):
            with collector.track_ai_call("openai", "summarize"):
                raise ValueError("Test hatası")
        
        assert collector.stats['total_calls'] == 1
        assert collector.stats['total_errors'] == 1
        assert collector.stats['model_stats']['openai']['errors'] == 1
    
    def test_start_metrics_server_without_prometheus(self, collector):
        """Prometheus olmadan metrik sunucusu başlatma testi"""
        with patch('metrics.PROMETHEUS_AVAILABLE', False):
            result = collector.start_metrics_server()
            assert result is False
    
    def test_start_metrics_server_with_prometheus(self, collector):
        """Prometheus ile metrik sunucusu başlatma testi"""
        mock_start_server = Mock()
        
        with patch('metrics.PROMETHEUS_AVAILABLE', True), \
             patch('metrics.start_http_server', mock_start_server), \
             patch('threading.Thread') as mock_thread:
            
            mock_thread_instance = Mock()
            mock_thread.return_value = mock_thread_instance
            
            result = collector.start_metrics_server(port=9001, host='127.0.0.1')
            
            assert result is True
            assert collector.metrics_server_running is True
            assert collector.metrics_server_port == 9001
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
    
    def test_start_metrics_server_already_running(self, collector):
        """Zaten çalışan metrik sunucusu testi"""
        collector.metrics_server_running = True
        
        result = collector.start_metrics_server()
        assert result is True  # Zaten çalışıyor, True döner
    
    def test_stop_metrics_server(self, collector):
        """Metrik sunucusu durdurma testi"""
        collector.metrics_server_running = True
        collector.stop_metrics_server()
        assert collector.metrics_server_running is False
    
    def test_get_metrics_summary(self, collector):
        """Metrik özeti alma testi"""
        # Test verisi ekle
        collector.log_ai_call("openai", "summarize", tokens_used=100, latency=1.5)
        collector.log_ai_call("gemini", "classify", tokens_used=50, latency=0.8)
        collector.log_ai_call("openai", "summarize", tokens_used=75, latency=1.2, error_type="APIError")
        
        summary = collector.get_metrics_summary()
        
        assert summary['metrics_enabled'] is False  # Prometheus yok
        assert summary['server_running'] is False
        assert summary['server_port'] == 9000
        assert summary['stats']['total_calls'] == 3
        assert summary['stats']['total_tokens'] == 225
        assert summary['stats']['total_errors'] == 1
        
        # Model özeti kontrolü
        assert 'model_summary' in summary
        assert 'openai' in summary['model_summary']
        assert 'gemini' in summary['model_summary']
        
        openai_stats = summary['model_summary']['openai']
        assert openai_stats['total_calls'] == 2
        assert openai_stats['total_tokens'] == 175
        assert openai_stats['total_errors'] == 1
        assert openai_stats['avg_latency'] == 1.35  # (1.5 + 1.2) / 2
        assert openai_stats['error_rate'] == 50.0  # 1/2 * 100
        
        gemini_stats = summary['model_summary']['gemini']
        assert gemini_stats['total_calls'] == 1
        assert gemini_stats['total_tokens'] == 50
        assert gemini_stats['total_errors'] == 0
        assert gemini_stats['avg_latency'] == 0.8
        assert gemini_stats['error_rate'] == 0.0
    
    def test_export_metrics(self, collector):
        """Metrik dışa aktarma testi"""
        # Test verisi ekle
        collector.log_ai_call("openai", "summarize", tokens_used=100, latency=1.5)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            result = collector.export_metrics(temp_file)
            assert result == temp_file
            
            # Dosyanın oluşturulduğunu kontrol et
            assert os.path.exists(temp_file)
            
            # JSON içeriğini kontrol et
            with open(temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert data['stats']['total_calls'] == 1
            assert data['stats']['total_tokens'] == 100
            assert 'export_time' in data
            
        finally:
            # Geçici dosyayı temizle
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_export_metrics_auto_filename(self, collector):
        """Otomatik dosya adı ile metrik dışa aktarma testi"""
        result = collector.export_metrics()
        
        assert result.startswith("metrics_export_")
        assert result.endswith(".json")
        assert os.path.exists(result)
        
        # Dosyayı temizle
        os.unlink(result)
    
    def test_reset_metrics(self, collector):
        """Metrik sıfırlama testi"""
        # Test verisi ekle
        collector.log_ai_call("openai", "summarize", tokens_used=100, latency=1.5)
        
        # Sıfırla
        collector.reset_metrics()
        
        assert collector.stats['total_calls'] == 0
        assert collector.stats['total_tokens'] == 0
        assert collector.stats['total_errors'] == 0
        assert collector.stats['model_stats'] == {}
        assert collector.stats['last_call_time'] is None

class TestGlobalFunctions:
    """Global fonksiyonlar testleri"""
    
    @pytest.fixture
    def mock_collector(self):
        """Mock collector oluştur"""
        with patch('metrics.get_metrics_collector') as mock_get:
            collector = Mock()
            mock_get.return_value = collector
            yield collector
    
    def test_get_metrics_collector(self):
        """Global collector alma testi"""
        # İlk çağrı
        collector1 = get_metrics_collector()
        assert collector1 is not None
        
        # İkinci çağrı (aynı instance)
        collector2 = get_metrics_collector()
        assert collector2 is collector1
    
    def test_log_ai_call_global(self, mock_collector):
        """Global AI çağrı loglama testi"""
        log_ai_call("openai", "summarize", tokens_used=100, latency=1.5)
        
        # Mock'ın çağrıldığını kontrol et
        mock_collector.log_ai_call.assert_called_once()
        call_args = mock_collector.log_ai_call.call_args
        # Parametreleri kontrol et (pozisyonel veya keyword olabilir)
        if call_args[1]:  # Keyword arguments varsa
            assert call_args[1].get('tokens_used') == 100
            assert call_args[1].get('latency') == 1.5
            assert call_args[1].get('error_type') is None
        else:  # Pozisyonel arguments
            assert call_args[0][2] == 100  # tokens_used
            assert call_args[0][3] == 1.5  # latency
            assert call_args[0][4] is None  # error_type
    
    def test_track_ai_call_global(self, mock_collector):
        """Global AI çağrı izleme testi"""
        # Mock context manager'ı ayarla
        mock_context = Mock()
        mock_context.__enter__ = Mock()
        mock_context.__exit__ = Mock()
        mock_collector.track_ai_call.return_value = mock_context
        
        with track_ai_call("openai", "summarize"):
            pass
        
        mock_collector.track_ai_call.assert_called_once_with("openai", "summarize")
    
    def test_start_metrics_server_global(self, mock_collector):
        """Global metrik sunucusu başlatma testi"""
        mock_collector.start_metrics_server.return_value = True
        
        result = start_metrics_server(port=9001, host='127.0.0.1')
        
        assert result is True
        mock_collector.start_metrics_server.assert_called_once_with(9001, '127.0.0.1')
    
    def test_get_metrics_summary_global(self, mock_collector):
        """Global metrik özeti alma testi"""
        mock_summary = {'test': 'data'}
        mock_collector.get_metrics_summary.return_value = mock_summary
        
        result = get_metrics_summary()
        
        assert result == mock_summary
        mock_collector.get_metrics_summary.assert_called_once()
    
    def test_export_metrics_global(self, mock_collector):
        """Global metrik dışa aktarma testi"""
        mock_collector.export_metrics.return_value = "test_export.json"
        
        result = export_metrics("test.json")
        
        assert result == "test_export.json"
        mock_collector.export_metrics.assert_called_once_with("test.json")
    
    def test_reset_metrics_global(self, mock_collector):
        """Global metrik sıfırlama testi"""
        reset_metrics()
        
        mock_collector.reset_metrics.assert_called_once()

class TestIntegration:
    """Entegrasyon testleri"""
    
    def test_ai_helper_integration(self):
        """AI Helper ile entegrasyon testi"""
        # AI Helper'ı mock'la
        with patch.dict('sys.modules', {
            'ai_helper': Mock(),
            'prometheus_client': Mock()
        }):
            from metrics import track_ai_call
            
            # Test çağrısı
            with track_ai_call("openai", "summarize"):
                time.sleep(0.1)
            
            # Metriklerin güncellendiğini kontrol et
            collector = get_metrics_collector()
            assert collector.stats['total_calls'] == 1
            assert collector.stats['model_stats']['openai']['calls'] == 1
    
    def test_multiple_concurrent_calls(self):
        """Eşzamanlı çağrı testi"""
        with patch.dict('sys.modules', {
            'prometheus_client': Mock()
        }):
            collector = get_metrics_collector()
            
            # Eşzamanlı çağrılar
            import threading
            
            def make_call():
                with collector.track_ai_call("openai", "summarize"):
                    time.sleep(0.1)
            
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=make_call)
                threads.append(thread)
                thread.start()
            
            # Tüm thread'lerin bitmesini bekle
            for thread in threads:
                thread.join()
            
            # Sonuçları kontrol et (eşzamanlı çağrılar nedeniyle sayı değişebilir)
            assert collector.stats['total_calls'] >= 5
            assert collector.stats['model_stats']['openai']['calls'] >= 5

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 