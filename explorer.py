#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Veri Keşif Modülü

Bu modül MySQL tablolarını analiz eder ve veri keşif işlemleri yapar.
Kolon analizi, null oranları, örnek veriler ve NLP için uygun metin alanlarını tespit eder.

Kullanım:
    python explorer.py --host localhost --user root --password pass --database test --table users
    python explorer.py --analyze-table users --host localhost --user root --password pass --database test
"""

import sqlalchemy as sa
import pandas as pd
import numpy as np
from collections import Counter
import re
import argparse
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

# Logging konfigürasyonu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataExplorer:
    """MySQL tablolarını analiz eden veri keşif sınıfı"""
    
    def __init__(self, engine=None, host: str = None, user: str = None, password: str = None, database: str = None, port: int = 3306):
        """
        DataExplorer sınıfını başlat
        
        Args:
            engine: SQLAlchemy engine (öncelikli)
            host: MySQL sunucu adresi (engine yoksa)
            user: Kullanıcı adı (engine yoksa)
            password: Şifre (engine yoksa)
            database: Veritabanı adı (engine yoksa)
            port: Port numarası (varsayılan: 3306, engine yoksa)
        """
        if engine is not None:
            self.engine = engine
            self.host = None
            self.user = None
            self.password = None
            self.database = None
            self.port = None
        else:
            self.host = host
            self.user = user
            self.password = password
            self.database = database
            self.port = port
            self.engine = None
            self._connect()
    
    def _connect(self):
        """MySQL veritabanına bağlan"""
        try:
            connection_string = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            self.engine = sa.create_engine(connection_string)
            logger.info(f"MySQL veritabanına başarıyla bağlandı: {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logger.error(f"Veritabanı bağlantısı başarısız: {e}")
            raise
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Tablo şemasını al
        
        Args:
            table_name: Tablo adı
            
        Returns:
            Tablo şema bilgileri
        """
        try:
            # Tablo meta verilerini al
            metadata = sa.MetaData()
            table = sa.Table(table_name, metadata, autoload_with=self.engine)
            
            schema_info = {
                'table_name': table_name,
                'columns': [],
                'total_columns': len(table.columns),
                'timestamp': datetime.now().isoformat()
            }
            
            for column in table.columns:
                column_info = {
                    'name': column.name,
                    'type': str(column.type),
                    'nullable': column.nullable,
                    'primary_key': column.primary_key,
                    'unique': column.unique,
                    'default': column.default
                }
                schema_info['columns'].append(column_info)
            
            logger.info(f"Tablo şeması alındı: {table_name} ({len(table.columns)} kolon)")
            return schema_info
            
        except Exception as e:
            logger.error(f"Tablo şeması alınamadı: {e}")
            raise
    
    def analyze_table(self, table_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """
        Tabloyu detaylı analiz et
        
        Args:
            table_name: Tablo adı
            sample_size: Analiz için örnek veri boyutu
            
        Returns:
            Detaylı analiz sonuçları
        """
        try:
            # Tablo şemasını al
            schema = self.get_table_schema(table_name)
            
            # Veriyi yükle (performans için örnek)
            query = f"SELECT * FROM {table_name} LIMIT {sample_size}"
            df = pd.read_sql(query, self.engine)
            
            analysis = {
                'table_name': table_name,
                'total_rows': self._get_table_row_count(table_name),
                'sample_size': len(df),
                'columns_analysis': {},
                'text_columns': [],
                'timestamp': datetime.now().isoformat()
            }
            
            # Her kolonu analiz et
            for column in df.columns:
                column_analysis = self._analyze_column(df, column)
                analysis['columns_analysis'][column] = column_analysis
                
                # Metin kolonlarını tespit et
                if column_analysis['is_text']:
                    analysis['text_columns'].append(column)
            
            logger.info(f"Tablo analizi tamamlandı: {table_name}")
            return analysis
            
        except Exception as e:
            logger.error(f"Tablo analizi başarısız: {e}")
            raise
    
    def _get_table_row_count(self, table_name: str) -> int:
        """Tablo satır sayısını al"""
        try:
            query = f"SELECT COUNT(*) as count FROM {table_name}"
            result = pd.read_sql(query, self.engine)
            return result['count'].iloc[0]
        except Exception as e:
            logger.warning(f"Satır sayısı alınamadı: {e}")
            return 0
    
    def _analyze_column(self, df: pd.DataFrame, column_name: str) -> Dict[str, Any]:
        """
        Tek bir kolonu analiz et
        
        Args:
            df: Veri çerçevesi
            column_name: Kolon adı
            
        Returns:
            Kolon analiz sonuçları
        """
        column_data = df[column_name]
        
        # Boş tablo kontrolü
        if len(column_data) == 0:
            analysis = {
                'name': column_name,
                'dtype': str(column_data.dtype),
                'total_values': 0,
                'null_count': 0,
                'null_percentage': 0.0,
                'unique_count': 0,
                'unique_percentage': 0.0,
                'is_text': False,
                'sample_values': [],
                'text_analysis': None
            }
        else:
            analysis = {
                'name': column_name,
                'dtype': str(column_data.dtype),
                'total_values': len(column_data),
                'null_count': column_data.isnull().sum(),
                'null_percentage': (column_data.isnull().sum() / len(column_data)) * 100,
                'unique_count': column_data.nunique(),
                'unique_percentage': (column_data.nunique() / len(column_data)) * 100,
                'is_text': self._is_text_column(column_data),
                'sample_values': self._get_sample_values(column_data),
                'text_analysis': None
            }
        
        # Metin kolonu ise detaylı analiz yap
        if analysis['is_text']:
            analysis['text_analysis'] = self._analyze_text_column(column_data)
        
        return analysis
    
    def _is_text_column(self, column_data: pd.Series) -> bool:
        """Kolonun metin tipinde olup olmadığını kontrol et"""
        # Object tipi ve string içerik kontrolü
        if column_data.dtype == 'object':
            # Null olmayan değerlerin %60'ı string ise metin kolonu
            non_null = column_data.dropna()
            if len(non_null) > 0:
                string_count = sum(isinstance(x, str) for x in non_null)
                return (string_count / len(non_null)) > 0.6
        return False
    
    def _get_sample_values(self, column_data: pd.Series, count: int = 5) -> List[Any]:
        """Örnek değerleri al"""
        non_null = column_data.dropna()
        if len(non_null) == 0:
            return []
        
        # Benzersiz değerlerden örnek al
        unique_values = non_null.unique()
        sample_size = min(count, len(unique_values))
        
        if sample_size == 0:
            return []
        
        # Rastgele örnek al
        sample_indices = np.random.choice(len(unique_values), sample_size, replace=False)
        samples = unique_values[sample_indices]
        
        # String değerleri kısalt
        result = []
        for sample in samples:
            if isinstance(sample, str) and len(sample) > 100:
                result.append(sample[:100] + "...")
            else:
                result.append(sample)
        
        return result
    
    def _analyze_text_column(self, column_data: pd.Series) -> Dict[str, Any]:
        """Metin kolonunu detaylı analiz et"""
        non_null = column_data.dropna()
        if len(non_null) == 0:
            return {}
        
        # Sadece string değerleri al
        text_values = [str(x) for x in non_null if isinstance(x, str)]
        
        if not text_values:
            return {}
        
        # Uzunluk analizi
        lengths = [len(text) for text in text_values]
        
        # Kelime analizi
        all_words = []
        for text in text_values:
            # Türkçe karakterleri koru, özel karakterleri temizle
            cleaned_text = re.sub(r'[^\w\sçğıöşüÇĞIİÖŞÜ]', ' ', text.lower())
            words = cleaned_text.split()
            all_words.extend(words)
        
        # En sık geçen kelimeler
        word_counts = Counter(all_words)
        most_common_words = word_counts.most_common(10)
        
        return {
            'total_texts': len(text_values),
            'min_length': min(lengths),
            'max_length': max(lengths),
            'avg_length': np.mean(lengths),
            'median_length': np.median(lengths),
            'shortest_text': min(text_values, key=len)[:100] + "..." if len(min(text_values, key=len)) > 100 else min(text_values, key=len),
            'longest_text': max(text_values, key=len)[:100] + "..." if len(max(text_values, key=len)) > 100 else max(text_values, key=len),
            'total_words': len(all_words),
            'unique_words': len(set(all_words)),
            'avg_words_per_text': len(all_words) / len(text_values),
            'most_common_words': most_common_words
        }
    
    def get_text_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        NLP için uygun metin kolonlarını tespit et
        
        Args:
            table_name: Tablo adı
            
        Returns:
            Metin kolonları listesi
        """
        try:
            # Tabloyu analiz et
            analysis = self.analyze_table(table_name)
            
            text_columns = []
            nlp_keywords = ['aciklama', 'icerik', 'istek', 'tanim', 'yorum', 'mesaj', 
                           'not', 'detay', 'açıklama', 'içerik', 'tanım', 'yorum']
            
            for column_name, column_analysis in analysis['columns_analysis'].items():
                if column_analysis['is_text']:
                    # NLP için uygunluk skoru hesapla
                    score = 0
                    
                    # Kolon adı kontrolü
                    column_lower = column_name.lower()
                    for keyword in nlp_keywords:
                        if keyword in column_lower:
                            score += 3
                    
                    # Veri kalitesi kontrolü
                    if column_analysis['null_percentage'] < 20:  # %20'den az null
                        score += 2
                    
                    if column_analysis['unique_percentage'] > 50:  # %50'den fazla benzersiz
                        score += 2
                    
                    # Metin analizi varsa
                    if column_analysis['text_analysis']:
                        text_analysis = column_analysis['text_analysis']
                        if text_analysis['avg_length'] > 20:  # Ortalama 20 karakterden uzun
                            score += 1
                        
                        if text_analysis['avg_words_per_text'] > 3:  # Ortalama 3 kelimeden fazla
                            score += 1
                    
                    text_columns.append({
                        'column_name': column_name,
                        'score': score,
                        'analysis': column_analysis
                    })
            
            # Skora göre sırala
            text_columns.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"NLP için {len(text_columns)} metin kolonu tespit edildi")
            return text_columns
            
        except Exception as e:
            logger.error(f"Metin kolonları tespit edilemedi: {e}")
            raise
    
    def export_analysis(self, table_name: str, output_file: str = None) -> str:
        """
        Analiz sonuçlarını JSON dosyasına kaydet
        
        Args:
            table_name: Tablo adı
            output_file: Çıktı dosyası (opsiyonel)
            
        Returns:
            Kaydedilen dosya yolu
        """
        try:
            # Tam analiz yap
            analysis = self.analyze_table(table_name)
            text_columns = self.get_text_columns(table_name)
            
            # Sonuçları birleştir
            result = {
                'table_analysis': analysis,
                'text_columns': text_columns,
                'export_timestamp': datetime.now().isoformat(),
                'explorer_version': '1.0.0'
            }
            
            # Dosya adını belirle
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"analysis_{table_name}_{timestamp}.json"
            
            # JSON dosyasına kaydet
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Analiz sonuçları kaydedildi: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Analiz sonuçları kaydedilemedi: {e}")
            raise
    
    def print_summary(self, table_name: str):
        """Analiz özetini konsola yazdır"""
        try:
            analysis = self.analyze_table(table_name)
            text_columns = self.get_text_columns(table_name)
            
            print(f"\n{'='*60}")
            print(f"📊 TABLO ANALİZ ÖZETİ: {table_name.upper()}")
            print(f"{'='*60}")
            
            print(f"📈 Genel Bilgiler:")
            print(f"   • Toplam Satır: {analysis['total_rows']:,}")
            print(f"   • Örnek Boyut: {analysis['sample_size']:,}")
            print(f"   • Toplam Kolon: {len(analysis['columns_analysis'])}")
            print(f"   • Metin Kolonları: {len(text_columns)}")
            
            print(f"\n📋 Kolon Analizi:")
            for column_name, column_analysis in analysis['columns_analysis'].items():
                print(f"   • {column_name}:")
                print(f"     - Tip: {column_analysis['dtype']}")
                print(f"     - Null Oranı: {column_analysis['null_percentage']:.1f}%")
                print(f"     - Benzersiz: {column_analysis['unique_percentage']:.1f}%")
                
                if column_analysis['is_text']:
                    text_analysis = column_analysis['text_analysis']
                    print(f"     - Ortalama Uzunluk: {text_analysis['avg_length']:.1f} karakter")
                    print(f"     - Ortalama Kelime: {text_analysis['avg_words_per_text']:.1f}")
            
            print(f"\n🔍 NLP İçin Önerilen Metin Kolonları:")
            for i, text_col in enumerate(text_columns[:5], 1):  # İlk 5'i göster
                print(f"   {i}. {text_col['column_name']} (Skor: {text_col['score']})")
                analysis = text_col['analysis']
                if analysis['text_analysis']:
                    ta = analysis['text_analysis']
                    print(f"      - Ortalama: {ta['avg_length']:.1f} karakter, {ta['avg_words_per_text']:.1f} kelime")
                    print(f"      - En sık kelimeler: {', '.join([word for word, _ in ta['most_common_words'][:3]])}")
            
            print(f"\n{'='*60}")
            
        except Exception as e:
            logger.error(f"Özet yazdırılamadı: {e}")
            raise

def main():
    """Ana CLI fonksiyonu"""
    parser = argparse.ArgumentParser(description='MySQL Tablo Veri Keşif Aracı')
    
    # Bağlantı parametreleri
    parser.add_argument('--host', default='localhost', help='MySQL sunucu adresi')
    parser.add_argument('--user', required=True, help='MySQL kullanıcı adı')
    parser.add_argument('--password', required=True, help='MySQL şifresi')
    parser.add_argument('--database', required=True, help='Veritabanı adı')
    parser.add_argument('--port', type=int, default=3306, help='MySQL port (varsayılan: 3306)')
    
    # İşlem parametreleri
    parser.add_argument('--table', required=True, help='Analiz edilecek tablo adı')
    parser.add_argument('--schema-only', action='store_true', help='Sadece şema bilgilerini al')
    parser.add_argument('--text-columns-only', action='store_true', help='Sadece metin kolonlarını tespit et')
    parser.add_argument('--export', help='Analiz sonuçlarını JSON dosyasına kaydet')
    parser.add_argument('--sample-size', type=int, default=1000, help='Analiz için örnek boyut (varsayılan: 1000)')
    
    args = parser.parse_args()
    
    try:
        # DataExplorer'ı başlat
        explorer = DataExplorer(
            host=args.host,
            user=args.user,
            password=args.password,
            database=args.database,
            port=args.port
        )
        
        if args.schema_only:
            # Sadece şema bilgilerini al
            schema = explorer.get_table_schema(args.table)
            print(json.dumps(schema, ensure_ascii=False, indent=2))
            
        elif args.text_columns_only:
            # Sadece metin kolonlarını tespit et
            text_columns = explorer.get_text_columns(args.table)
            print(json.dumps(text_columns, ensure_ascii=False, indent=2))
            
        else:
            # Tam analiz yap
            if args.export:
                output_file = explorer.export_analysis(args.table, args.export)
                print(f"✅ Analiz sonuçları kaydedildi: {output_file}")
            
            # Özet yazdır
            explorer.print_summary(args.table)
    
    except Exception as e:
        logger.error(f"İşlem başarısız: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 