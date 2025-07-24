#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Veri Keşif Modülü Test Dosyası

Bu dosya explorer.py modülünün test fonksiyonlarını içerir.
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Test edilecek modülü import et
try:
    from explorer import DataExplorer
except ImportError:
    pytest.skip("explorer modülü bulunamadı", allow_module_level=True)

class TestDataExplorer:
    """DataExplorer sınıfı testleri"""
    
    @pytest.fixture
    def mock_engine(self):
        """Mock SQLAlchemy engine"""
        mock_engine = Mock()
        return mock_engine
    
    @pytest.fixture
    def sample_dataframe(self):
        """Test için örnek veri çerçevesi"""
        data = {
            'id': [1, 2, 3, 4, 5],
            'name': ['Ahmet', 'Mehmet', 'Ayşe', 'Fatma', 'Ali'],
            'description': [
                'Bu bir açıklama metnidir',
                'Başka bir açıklama',
                'Üçüncü açıklama metni',
                'Dördüncü açıklama',
                'Beşinci açıklama metni'
            ],
            'age': [25, 30, 35, 28, 32],
            'email': ['ahmet@test.com', 'mehmet@test.com', 'ayse@test.com', 'fatma@test.com', 'ali@test.com'],
            'notes': [
                'Bu bir not metnidir ve oldukça uzun olabilir',
                'Kısa not',
                'Orta uzunlukta bir not metni',
                None,
                'Son not metni'
            ]
        }
        return pd.DataFrame(data)
    
    @pytest.fixture
    def explorer(self):
        """Test için DataExplorer instance'ı"""
        with patch('explorer.sa.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine
            
            explorer = DataExplorer(
                host='localhost',
                user='test_user',
                password='test_pass',
                database='test_db'
            )
            return explorer
    
    def test_init(self):
        """DataExplorer başlatma testi"""
        with patch('explorer.sa.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine
            
            explorer = DataExplorer(
                host='test_host',
                user='test_user',
                password='test_pass',
                database='test_db',
                port=3307
            )
            
            assert explorer.host == 'test_host'
            assert explorer.user == 'test_user'
            assert explorer.password == 'test_pass'
            assert explorer.database == 'test_db'
            assert explorer.port == 3307
            assert explorer.engine == mock_engine
    
    def test_get_table_schema(self, explorer):
        """Tablo şeması alma testi"""
        # Mock tablo ve kolonlar
        mock_table = Mock()
        mock_columns = []
        
        for i, col_name in enumerate(['id', 'name', 'description']):
            mock_col = Mock()
            mock_col.name = col_name
            mock_col.type = f'VARCHAR({50 + i*10})'
            mock_col.nullable = True
            mock_col.primary_key = (i == 0)  # İlk kolon primary key
            mock_col.unique = False
            mock_col.default = None
            mock_columns.append(mock_col)
        
        mock_table.columns = mock_columns
        
        with patch('explorer.sa.MetaData') as mock_metadata, \
             patch('explorer.sa.Table') as mock_table_class:
            
            mock_metadata_instance = Mock()
            mock_metadata.return_value = mock_metadata_instance
            
            mock_table_class.return_value = mock_table
            
            schema = explorer.get_table_schema('test_table')
            
            assert schema['table_name'] == 'test_table'
            assert schema['total_columns'] == 3
            assert len(schema['columns']) == 3
            assert schema['columns'][0]['name'] == 'id'
            assert schema['columns'][0]['primary_key'] == True
    
    def test_analyze_table(self, explorer, sample_dataframe):
        """Tablo analizi testi"""
        with patch.object(explorer, 'get_table_schema') as mock_schema, \
             patch.object(explorer, '_get_table_row_count') as mock_count, \
             patch('explorer.pd.read_sql') as mock_read_sql:
            
            mock_schema.return_value = {'table_name': 'test_table', 'columns': []}
            mock_count.return_value = 100
            mock_read_sql.return_value = sample_dataframe
            
            analysis = explorer.analyze_table('test_table')
            
            assert analysis['table_name'] == 'test_table'
            assert analysis['total_rows'] == 100
            assert analysis['sample_size'] == 5
            assert len(analysis['columns_analysis']) == 6
            assert 'text_columns' in analysis
    
    def test_analyze_column(self, explorer, sample_dataframe):
        """Kolon analizi testi"""
        column_analysis = explorer._analyze_column(sample_dataframe, 'description')
        
        assert column_analysis['name'] == 'description'
        assert column_analysis['dtype'] == 'object'
        assert column_analysis['total_values'] == 5
        assert column_analysis['null_count'] == 0
        assert column_analysis['null_percentage'] == 0.0
        assert column_analysis['unique_count'] == 5
        assert column_analysis['unique_percentage'] == 100.0
        assert column_analysis['is_text'] == True
        assert len(column_analysis['sample_values']) <= 5
        assert column_analysis['text_analysis'] is not None
    
    def test_is_text_column(self, explorer):
        """Metin kolonu tespiti testi"""
        # Metin kolonu
        text_data = pd.Series(['a', 'b', 'c', 'd', 'e'])
        assert explorer._is_text_column(text_data) == True
        
        # Sayısal kolon
        numeric_data = pd.Series([1, 2, 3, 4, 5])
        assert explorer._is_text_column(numeric_data) == False
        
        # Karışık veri (çoğunluk string)
        mixed_data = pd.Series(['a', 1, 'b', 2, 'c', 'd'])
        assert explorer._is_text_column(mixed_data) == True
        
        # Boş veri
        empty_data = pd.Series([])
        assert explorer._is_text_column(empty_data) == False
    
    def test_get_sample_values(self, explorer):
        """Örnek değer alma testi"""
        # Normal veri
        data = pd.Series(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'])
        samples = explorer._get_sample_values(data, count=3)
        assert len(samples) == 3
        assert all(isinstance(s, str) for s in samples)
        
        # Boş veri
        empty_data = pd.Series([])
        samples = explorer._get_sample_values(empty_data)
        assert len(samples) == 0
        
        # Uzun string değerler
        long_data = pd.Series(['a' * 200, 'b' * 150, 'c'])
        samples = explorer._get_sample_values(long_data, count=2)
        assert len(samples) == 2
        assert all(len(s) <= 103 for s in samples)  # 100 + "..."
    
    def test_analyze_text_column(self, explorer):
        """Metin kolonu detaylı analizi testi"""
        text_data = pd.Series([
            'Bu bir test metnidir',
            'Başka bir test metni',
            'Üçüncü test metni',
            'Dördüncü test metni',
            'Beşinci test metni'
        ])
        
        analysis = explorer._analyze_text_column(text_data)
        
        assert analysis['total_texts'] == 5
        assert analysis['min_length'] > 0
        assert analysis['max_length'] > 0
        assert analysis['avg_length'] > 0
        assert analysis['total_words'] > 0
        assert analysis['unique_words'] > 0
        assert analysis['avg_words_per_text'] > 0
        assert len(analysis['most_common_words']) > 0
        
        # Türkçe kelime kontrolü
        words = [word for word, _ in analysis['most_common_words']]
        assert 'test' in words or 'metni' in words
    
    def test_get_text_columns(self, explorer):
        """Metin kolonları tespiti testi"""
        with patch.object(explorer, 'analyze_table') as mock_analyze:
            # Mock analiz sonucu
            mock_analysis = {
                'columns_analysis': {
                    'id': {
                        'is_text': False,
                        'null_percentage': 0,
                        'unique_percentage': 100
                    },
                    'name': {
                        'is_text': True,
                        'null_percentage': 0,
                        'unique_percentage': 80,
                        'text_analysis': {
                            'avg_length': 10,
                            'avg_words_per_text': 2
                        }
                    },
                    'description': {
                        'is_text': True,
                        'null_percentage': 10,
                        'unique_percentage': 90,
                        'text_analysis': {
                            'avg_length': 50,
                            'avg_words_per_text': 8
                        }
                    },
                    'aciklama': {
                        'is_text': True,
                        'null_percentage': 5,
                        'unique_percentage': 85,
                        'text_analysis': {
                            'avg_length': 30,
                            'avg_words_per_text': 5
                        }
                    }
                }
            }
            mock_analyze.return_value = mock_analysis
            
            text_columns = explorer.get_text_columns('test_table')
            
            assert len(text_columns) == 3
            # 'aciklama' kolonu en yüksek skor almalı (keyword + iyi veri kalitesi)
            assert text_columns[0]['column_name'] == 'aciklama'
            assert text_columns[0]['score'] > text_columns[1]['score']
    
    def test_export_analysis(self, explorer):
        """Analiz sonuçlarını dışa aktarma testi"""
        with patch.object(explorer, 'analyze_table') as mock_analyze, \
             patch.object(explorer, 'get_text_columns') as mock_text_columns:
            
            mock_analyze.return_value = {'table_name': 'test_table'}
            mock_text_columns.return_value = [{'column_name': 'description'}]
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                output_file = explorer.export_analysis('test_table', tmp_path)
                
                assert output_file == tmp_path
                assert os.path.exists(tmp_path)
                
                # JSON dosyasını oku ve kontrol et
                with open(tmp_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                assert 'table_analysis' in data
                assert 'text_columns' in data
                assert 'export_timestamp' in data
                assert 'explorer_version' in data
                
            finally:
                # Test dosyasını temizle
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
    
    def test_get_table_row_count(self, explorer):
        """Tablo satır sayısı alma testi"""
        with patch('explorer.pd.read_sql') as mock_read_sql:
            mock_df = pd.DataFrame({'count': [100]})
            mock_read_sql.return_value = mock_df
            
            count = explorer._get_table_row_count('test_table')
            assert count == 100
    
    def test_error_handling(self, explorer):
        """Hata yönetimi testi"""
        # Bağlantı hatası
        with patch('explorer.sa.create_engine', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception):
                DataExplorer('host', 'user', 'pass', 'db')
        
        # Tablo bulunamadı hatası
        with patch.object(explorer, 'engine') as mock_engine:
            mock_engine.execute.side_effect = Exception("Table not found")
            
            with pytest.raises(Exception):
                explorer.get_table_schema('nonexistent_table')

class TestDataExplorerIntegration:
    """Entegrasyon testleri (gerçek veritabanı gerektirmez)"""
    
    def test_full_workflow(self):
        """Tam iş akışı testi"""
        with patch('explorer.sa.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine
            
            explorer = DataExplorer('host', 'user', 'pass', 'db')
            
            # Mock veri
            sample_data = {
                'id': [1, 2, 3],
                'name': ['Test1', 'Test2', 'Test3'],
                'description': ['Açıklama 1', 'Açıklama 2', 'Açıklama 3']
            }
            df = pd.DataFrame(sample_data)
            
            with patch.object(explorer, 'get_table_schema') as mock_schema, \
                 patch.object(explorer, '_get_table_row_count') as mock_count, \
                 patch('explorer.pd.read_sql') as mock_read_sql:
                
                mock_schema.return_value = {'table_name': 'test', 'columns': []}
                mock_count.return_value = 3
                mock_read_sql.return_value = df
                
                # Tam analiz yap
                analysis = explorer.analyze_table('test_table')
                text_columns = explorer.get_text_columns('test_table')
                
                assert analysis['table_name'] == 'test_table'
                assert len(text_columns) > 0
                
                # En az bir metin kolonu olmalı
                assert any(col['column_name'] == 'description' for col in text_columns)

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 