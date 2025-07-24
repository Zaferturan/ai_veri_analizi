"""
AI Helper Test Modülü - Ollama Destekli

Bu modül, AI Helper sınıfının Ollama entegrasyonunu test eder.
"""

import pytest
import unittest.mock as mock
from unittest.mock import Mock, patch
import json
import requests
from ai_helper import AIHelper

class TestAIHelper:
    """AI Helper test sınıfı"""
    
    def setup_method(self):
        """Her test öncesi çalışır"""
        self.ai_helper = AIHelper()
        
    def test_init(self):
        """AI Helper başlatma testi"""
        assert self.ai_helper.ollama_host == "http://localhost:11434"
        assert isinstance(self.ai_helper.available_models, list)
        
    @patch('requests.get')
    def test_get_available_models_success(self, mock_get):
        """Mevcut modelleri alma testi - başarılı"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama3:latest'},
                {'name': 'qwen2.5-coder:32b-instruct-q4_0'}
            ]
        }
        mock_get.return_value = mock_response
        
        models = self.ai_helper._get_available_models()
        assert models == ['llama3:latest', 'qwen2.5-coder:32b-instruct-q4_0']
        
    @patch('requests.get')
    def test_get_available_models_error(self, mock_get):
        """Mevcut modelleri alma testi - hata"""
        mock_get.side_effect = Exception("Bağlantı hatası")
        
        models = self.ai_helper._get_available_models()
        assert models == []
        
    @patch('requests.post')
    def test_call_ollama_success(self, mock_post):
        """Ollama çağrısı testi - başarılı"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'Test yanıtı'}
        mock_post.return_value = mock_response
        
        result = self.ai_helper._call_ollama('llama3:latest', 'Test prompt')
        assert result == 'Test yanıtı'
        
    @patch('requests.post')
    def test_call_ollama_error(self, mock_post):
        """Ollama çağrısı testi - hata"""
        mock_post.side_effect = Exception("API hatası")
        
        result = self.ai_helper._call_ollama('llama3:latest', 'Test prompt')
        assert result == ""
        
    @patch.object(AIHelper, '_call_ollama')
    def test_summarize_texts(self, mock_call):
        """Metin özetleme testi"""
        mock_call.return_value = "Bu bir özet."
        
        texts = ["Metin 1", "Metin 2", "Metin 3"]
        result = self.ai_helper.summarize_texts(texts, 'llama3:latest')
        
        assert 'summary' in result
        assert result['summary'] == "Bu bir özet."
        assert result['model'] == 'llama3:latest'
        assert result['text_count'] == 3
        
    @patch.object(AIHelper, '_call_ollama')
    def test_classify_texts(self, mock_call):
        """Metin sınıflandırma testi"""
        mock_call.return_value = "Teknik"
        
        texts = ["Bu teknik bir metin", "Bu genel bir metin"]
        result = self.ai_helper.classify_texts(texts, 'llama3:latest')
        
        assert 'classifications' in result
        assert len(result['classifications']) == 2
        assert result['model'] == 'llama3:latest'
        
    @patch.object(AIHelper, '_call_ollama')
    def test_cluster_texts(self, mock_call):
        """Metin kümelendirme testi"""
        mock_call.return_value = "Grup 1: Teknik - Metinler: 1,2"
        
        texts = ["Teknik metin 1", "Teknik metin 2", "Genel metin"]
        result = self.ai_helper.cluster_texts(texts, 'llama3:latest')
        
        assert 'clusters' in result
        assert result['model'] == 'llama3:latest'
        assert result['text_count'] == 3
        
    @patch.object(AIHelper, '_call_ollama')
    def test_analyze_trends(self, mock_call):
        """Trend analizi testi"""
        mock_call.return_value = "Artış trendi gözleniyor"
        
        texts = ["Ocak verisi", "Şubat verisi", "Mart verisi"]
        dates = ["2024-01-01", "2024-02-01", "2024-03-01"]
        result = self.ai_helper.analyze_trends(texts, dates, 'llama3:latest')
        
        assert 'trends' in result
        assert result['model'] == 'llama3:latest'
        assert result['text_count'] == 3
        
    @patch('requests.get')
    def test_test_connection_success(self, mock_get):
        """Bağlantı testi - başarılı"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.ai_helper.test_connection()
        assert result == True
        
    @patch('requests.get')
    def test_test_connection_error(self, mock_get):
        """Bağlantı testi - hata"""
        mock_get.side_effect = Exception("Bağlantı hatası")
        
        result = self.ai_helper.test_connection()
        assert result == False
        
    def test_get_available_models(self):
        """Mevcut modelleri döndürme testi"""
        models = self.ai_helper.get_available_models()
        assert isinstance(models, list)

def test_ai_helper_integration():
    """Entegrasyon testi"""
    # Gerçek Ollama bağlantısı olmadan test
    with patch('requests.get') as mock_get:
        mock_get.side_effect = Exception("Test için bağlantı engellendi")
        
        ai_helper = AIHelper()
        assert ai_helper.available_models == []
        assert ai_helper.test_connection() == False

if __name__ == "__main__":
    pytest.main([__file__]) 