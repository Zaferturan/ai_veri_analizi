#!/usr/bin/env python3
"""
Prometheus Uyumlu Metrik İzleme Modülü

Bu modül, AI fonksiyonlarının performansını ve kullanımını izlemek için
Prometheus uyumlu metrikler sağlar.

Özellikler:
- AI çağrı sayısı izleme
- Token kullanımı izleme
- Yanıt süresi (latency) izleme
- Model bazlı ayrıştırma
- HTTP endpoint ile metrik erişimi
"""

import time
import logging
import threading
from typing import Optional, Dict, Any
from contextlib import contextmanager
import argparse
from pathlib import Path
import json
from datetime import datetime

# Prometheus client import
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("Uyarı: prometheus_client kütüphanesi bulunamadı. Metrik izleme devre dışı.")
    print("Kurulum: pip install prometheus_client")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MetricsCollector:
    """Prometheus uyumlu metrik toplayıcı"""
    
    def __init__(self):
        self.metrics_initialized = False
        self.metrics_server_running = False
        self.metrics_server_thread = None
        self.metrics_server_port = 9000
        
        # Metrik objeleri
        self.ai_call_counter = None
        self.ai_token_counter = None
        self.ai_latency_histogram = None
        self.ai_active_requests = None
        self.ai_error_counter = None
        
        # İstatistikler
        self.stats = {
            'total_calls': 0,
            'total_tokens': 0,
            'total_errors': 0,
            'model_stats': {},
            'last_call_time': None
        }
        
        if PROMETHEUS_AVAILABLE:
            self.init_metrics()
    
    def init_metrics(self):
        """Prometheus metrik objelerini başlat"""
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus client mevcut değil, metrikler devre dışı")
            return
        
        try:
            # AI çağrı sayacı (model bazlı)
            self.ai_call_counter = Counter(
                'ai_calls_total',
                'Toplam AI çağrı sayısı',
                ['model', 'action']
            )
            
            # Token kullanım sayacı (model bazlı)
            self.ai_token_counter = Counter(
                'ai_tokens_total',
                'Toplam token kullanımı',
                ['model', 'action']
            )
            
            # Yanıt süresi histogramı (model bazlı)
            self.ai_latency_histogram = Histogram(
                'ai_latency_seconds',
                'AI yanıt süresi (saniye)',
                ['model', 'action'],
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
            )
            
            # Aktif istek sayısı (model bazlı)
            self.ai_active_requests = Gauge(
                'ai_active_requests',
                'Aktif AI istek sayısı',
                ['model', 'action']
            )
            
            # Hata sayacı (model bazlı)
            self.ai_error_counter = Counter(
                'ai_errors_total',
                'Toplam AI hata sayısı',
                ['model', 'action', 'error_type']
            )
            
            self.metrics_initialized = True
            logger.info("Prometheus metrikleri başlatıldı")
            
        except Exception as e:
            logger.error(f"Metrik başlatma hatası: {e}")
            self.metrics_initialized = False
    
    def log_ai_call(self, model_name: str, action: str, tokens_used: int = 0, 
                   latency: float = 0.0, error_type: Optional[str] = None):
        """
        AI çağrısını logla ve metrikleri güncelle
        
        Args:
            model_name: AI model adı (openai, gemini, vb.)
            action: Yapılan işlem (summarize, cluster, classify, vb.)
            tokens_used: Kullanılan token sayısı
            latency: Yanıt süresi (saniye)
            error_type: Hata tipi (varsa)
        """
        try:
            # İstatistikleri güncelle
            self.stats['total_calls'] += 1
            self.stats['total_tokens'] += tokens_used
            self.stats['last_call_time'] = datetime.now().isoformat()
            
            # Model bazlı istatistikler
            if model_name not in self.stats['model_stats']:
                self.stats['model_stats'][model_name] = {
                    'calls': 0,
                    'tokens': 0,
                    'errors': 0,
                    'total_latency': 0.0
                }
            
            self.stats['model_stats'][model_name]['calls'] += 1
            self.stats['model_stats'][model_name]['tokens'] += tokens_used
            self.stats['model_stats'][model_name]['total_latency'] += latency
            
            if error_type:
                self.stats['total_errors'] += 1
                self.stats['model_stats'][model_name]['errors'] += 1
            
            # Prometheus metriklerini güncelle
            if self.metrics_initialized:
                # Çağrı sayacı
                self.ai_call_counter.labels(model=model_name, action=action).inc()
                
                # Token sayacı
                if tokens_used > 0:
                    self.ai_token_counter.labels(model=model_name, action=action).inc(tokens_used)
                
                # Yanıt süresi histogramı
                if latency > 0:
                    self.ai_latency_histogram.labels(model=model_name, action=action).observe(latency)
                
                # Hata sayacı
                if error_type:
                    self.ai_error_counter.labels(
                        model=model_name, 
                        action=action, 
                        error_type=error_type
                    ).inc()
            
            logger.info(f"AI çağrısı loglandı: {model_name}/{action} - "
                       f"Token: {tokens_used}, Süre: {latency:.3f}s")
            
        except Exception as e:
            logger.error(f"Metrik loglama hatası: {e}")
    
    @contextmanager
    def track_ai_call(self, model_name: str, action: str):
        """
        AI çağrısını otomatik olarak izleyen context manager
        
        Usage:
            with metrics.track_ai_call("openai", "summarize"):
                # AI çağrısı burada yapılır
                result = ai_helper.summarize_texts(texts)
        """
        start_time = time.time()
        error_type = None
        
        try:
            # Aktif istek sayısını artır
            if self.metrics_initialized:
                self.ai_active_requests.labels(model=model_name, action=action).inc()
            
            yield
            
        except Exception as e:
            error_type = type(e).__name__
            raise
            
        finally:
            # Aktif istek sayısını azalt
            if self.metrics_initialized:
                self.ai_active_requests.labels(model=model_name, action=action).dec()
            
            # Metrikleri logla
            latency = time.time() - start_time
            self.log_ai_call(model_name, action, latency=latency, error_type=error_type)
    
    def start_metrics_server(self, port: int = 9000, host: str = '0.0.0.0'):
        """
        Prometheus metrik sunucusunu başlat
        
        Args:
            port: Sunucu portu
            host: Sunucu host adresi
        """
        if not PROMETHEUS_AVAILABLE:
            logger.error("Prometheus client mevcut değil, metrik sunucusu başlatılamıyor")
            return False
        
        if self.metrics_server_running:
            logger.warning("Metrik sunucusu zaten çalışıyor")
            return True
        
        try:
            def start_server():
                try:
                    start_http_server(port, addr=host)
                    logger.info(f"Prometheus metrik sunucusu başlatıldı: http://{host}:{port}/metrics")
                except Exception as e:
                    logger.error(f"Metrik sunucusu başlatma hatası: {e}")
            
            # Ayrı thread'de başlat
            self.metrics_server_thread = threading.Thread(target=start_server, daemon=True)
            self.metrics_server_thread.start()
            
            self.metrics_server_running = True
            self.metrics_server_port = port
            
            return True
            
        except Exception as e:
            logger.error(f"Metrik sunucusu başlatma hatası: {e}")
            return False
    
    def stop_metrics_server(self):
        """Metrik sunucusunu durdur"""
        if self.metrics_server_running:
            logger.info("Metrik sunucusu durduruldu")
            self.metrics_server_running = False
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Mevcut metrik özetini döndür"""
        summary = {
            'metrics_enabled': self.metrics_initialized,
            'server_running': self.metrics_server_running,
            'server_port': self.metrics_server_port,
            'stats': self.stats.copy(),
            'prometheus_available': PROMETHEUS_AVAILABLE
        }
        
        # Model bazlı özet istatistikler
        if self.stats['model_stats']:
            summary['model_summary'] = {}
            for model, stats in self.stats['model_stats'].items():
                avg_latency = stats['total_latency'] / stats['calls'] if stats['calls'] > 0 else 0
                summary['model_summary'][model] = {
                    'total_calls': stats['calls'],
                    'total_tokens': stats['tokens'],
                    'total_errors': stats['errors'],
                    'avg_latency': round(avg_latency, 3),
                    'error_rate': round(stats['errors'] / stats['calls'] * 100, 2) if stats['calls'] > 0 else 0
                }
        
        return summary
    
    def export_metrics(self, output_file: str = None) -> str:
        """
        Metrikleri JSON dosyasına dışa aktar
        
        Args:
            output_file: Çıktı dosya adı (opsiyonel)
            
        Returns:
            Kaydedilen dosya yolu
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"metrics_export_{timestamp}.json"
        
        try:
            metrics_data = self.get_metrics_summary()
            metrics_data['export_time'] = datetime.now().isoformat()
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Metrikler dışa aktarıldı: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Metrik dışa aktarma hatası: {e}")
            return ""
    
    def reset_metrics(self):
        """Tüm metrikleri sıfırla"""
        self.stats = {
            'total_calls': 0,
            'total_tokens': 0,
            'total_errors': 0,
            'model_stats': {},
            'last_call_time': None
        }
        logger.info("Metrikler sıfırlandı")

# Global metrics instance
_metrics_collector = None

def get_metrics_collector() -> MetricsCollector:
    """Global metrics collector instance'ını döndür"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

def log_ai_call(model_name: str, action: str, tokens_used: int = 0, 
               latency: float = 0.0, error_type: Optional[str] = None):
    """Global AI çağrı loglama fonksiyonu"""
    collector = get_metrics_collector()
    collector.log_ai_call(model_name, action, tokens_used, latency, error_type)

@contextmanager
def track_ai_call(model_name: str, action: str):
    """Global AI çağrı izleme context manager'ı"""
    collector = get_metrics_collector()
    with collector.track_ai_call(model_name, action):
        yield

def start_metrics_server(port: int = 9000, host: str = '0.0.0.0') -> bool:
    """Global metrik sunucusu başlatma fonksiyonu"""
    collector = get_metrics_collector()
    return collector.start_metrics_server(port, host)

def get_metrics_summary() -> Dict[str, Any]:
    """Global metrik özeti alma fonksiyonu"""
    collector = get_metrics_collector()
    return collector.get_metrics_summary()

def export_metrics(output_file: str = None) -> str:
    """Global metrik dışa aktarma fonksiyonu"""
    collector = get_metrics_collector()
    return collector.export_metrics(output_file)

def reset_metrics():
    """Global metrik sıfırlama fonksiyonu"""
    collector = get_metrics_collector()
    collector.reset_metrics()

def main():
    """CLI arayüzü"""
    parser = argparse.ArgumentParser(description="Prometheus Uyumlu Metrik İzleme Sistemi")
    parser.add_argument('--action', choices=['start-server', 'summary', 'export', 'reset', 'test'],
                       default='summary', help='Yapılacak işlem')
    parser.add_argument('--port', type=int, default=9000, help='Metrik sunucusu portu')
    parser.add_argument('--host', default='0.0.0.0', help='Metrik sunucusu host adresi')
    parser.add_argument('--output', help='Dışa aktarma dosya adı')
    
    args = parser.parse_args()
    
    collector = get_metrics_collector()
    
    if args.action == 'start-server':
        success = collector.start_metrics_server(args.port, args.host)
        if success:
            print(f"✅ Metrik sunucusu başlatıldı: http://{args.host}:{args.port}/metrics")
            print("Sunucuyu durdurmak için Ctrl+C tuşlayın...")
            try:
                # Sunucuyu çalışır durumda tut
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Metrik sunucusu durduruldu")
        else:
            print("❌ Metrik sunucusu başlatılamadı")
    
    elif args.action == 'summary':
        summary = collector.get_metrics_summary()
        print("📊 Metrik Özeti:")
        print(f"  Metrikler Aktif: {summary['metrics_enabled']}")
        print(f"  Sunucu Çalışıyor: {summary['server_running']}")
        print(f"  Sunucu Portu: {summary['server_port']}")
        print(f"  Prometheus Mevcut: {summary['prometheus_available']}")
        print(f"  Toplam Çağrı: {summary['stats']['total_calls']}")
        print(f"  Toplam Token: {summary['stats']['total_tokens']}")
        print(f"  Toplam Hata: {summary['stats']['total_errors']}")
        
        if summary['stats']['last_call_time']:
            print(f"  Son Çağrı: {summary['stats']['last_call_time']}")
        
        if 'model_summary' in summary:
            print("\n📈 Model Bazlı İstatistikler:")
            for model, stats in summary['model_summary'].items():
                print(f"  {model.upper()}:")
                print(f"    Çağrı: {stats['total_calls']}")
                print(f"    Token: {stats['total_tokens']}")
                print(f"    Hata: {stats['total_errors']} ({stats['error_rate']}%)")
                print(f"    Ort. Süre: {stats['avg_latency']}s")
    
    elif args.action == 'export':
        output_file = collector.export_metrics(args.output)
        if output_file:
            print(f"✅ Metrikler dışa aktarıldı: {output_file}")
        else:
            print("❌ Metrik dışa aktarma hatası")
    
    elif args.action == 'reset':
        collector.reset_metrics()
        print("✅ Metrikler sıfırlandı")
    
    elif args.action == 'test':
        print("🧪 Test metrikleri oluşturuluyor...")
        
        # Test çağrıları
        with collector.track_ai_call("openai", "summarize"):
            time.sleep(0.5)  # Simüle edilmiş işlem
        
        with collector.track_ai_call("gemini", "classify"):
            time.sleep(0.3)  # Simüle edilmiş işlem
        
        # Hata simülasyonu
        try:
            with collector.track_ai_call("openai", "cluster"):
                raise Exception("Test hatası")
        except:
            pass
        
        print("✅ Test metrikleri oluşturuldu")
        print("Özet için: python metrics.py --action summary")

if __name__ == "__main__":
    main() 