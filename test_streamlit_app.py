"""
Streamlit Uygulaması Test Modülü

Bu modül, streamlit_app.py dosyasındaki StreamlitApp sınıfının
temel fonksiyonlarını test eder.

Test Kapsamı:
- Session state yönetimi
- Veritabanı bağlantı formları
- Tablo analizi fonksiyonları
- AI analizi entegrasyonu
"""

import pytest
import pandas as pd
import sqlalchemy as sa
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Test için gerekli modülleri mock'la
sys.modules['streamlit'] = Mock()
sys.modules['streamlit'].session_state = {}

# Torch ve diğer modülleri mock'la
sys.modules['torch'] = Mock()
sys.modules['sentence_transformers'] = Mock()
sys.modules['transformers'] = Mock()
sys.modules['dotenv'] = Mock()

class TestStreamlitApp:
    """StreamlitApp sınıfı testleri"""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Streamlit modülünü mock'la"""
        with patch.dict('sys.modules', {'streamlit': Mock()}):
            import streamlit as st
            # Session state'i object olarak mock'la
            st.session_state = Mock()
            st.session_state.__getitem__ = Mock(side_effect=lambda key: st.session_state._get(key))
            st.session_state.__setitem__ = Mock(side_effect=lambda key, value: st.session_state._set(key, value))
            st.session_state._data = {}
            st.session_state._get = Mock(side_effect=lambda key: st.session_state._data.get(key))
            st.session_state._set = Mock(side_effect=lambda key, value: st.session_state._data.update({key: value}))
            
            # Sidebar context manager mock'u
            sidebar_mock = Mock()
            sidebar_mock.__enter__ = Mock(return_value=sidebar_mock)
            sidebar_mock.__exit__ = Mock(return_value=None)
            st.sidebar = sidebar_mock
            
            # Form context manager mock'u
            form_mock = Mock()
            form_mock.__enter__ = Mock(return_value=form_mock)
            form_mock.__exit__ = Mock(return_value=None)
            st.form = Mock(return_value=form_mock)
            
            yield st
            
    @pytest.fixture
    def app(self, mock_streamlit):
        """StreamlitApp instance'ı oluştur"""
        with patch('streamlit_app.st', mock_streamlit):
            from streamlit_app import StreamlitApp
            return StreamlitApp()
            
    @pytest.fixture
    def mock_engine(self):
        """SQLAlchemy engine mock'u"""
        engine = Mock()
        # Context manager mock'u
        connection_mock = Mock()
        connection_mock.__enter__ = Mock(return_value=connection_mock)
        connection_mock.__exit__ = Mock(return_value=None)
        connection_mock.execute = Mock(return_value=None)
        engine.connect = Mock(return_value=connection_mock)
        return engine
        
    @pytest.fixture
    def sample_dataframe(self):
        """Test için örnek DataFrame"""
        return pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'text': ['Bu bir test metni', 'Başka bir metin', 'Üçüncü metin', 'Dördüncü metin', 'Beşinci metin'],
            'category': ['A', 'B', 'A', 'C', 'B'],
            'date': pd.date_range('2024-01-01', periods=5)
        })
        
    def test_init(self, app):
        """StreamlitApp başlatma testi"""
        assert app.engine is None
        assert app.explorer is None
        assert app.ai_helper is None
        assert app.cache is None
        assert app.connection_status is False
        
    def test_init_session_state(self, app, mock_streamlit):
        """Session state başlatma testi"""
        app.init_session_state()
        
        assert 'connection_established' in mock_streamlit.session_state
        assert 'selected_table' in mock_streamlit.session_state
        assert 'table_data' in mock_streamlit.session_state
        assert 'analysis_results' in mock_streamlit.session_state
        
        assert mock_streamlit.session_state['connection_established'] is False
        assert mock_streamlit.session_state['selected_table'] is None
        assert mock_streamlit.session_state['table_data'] is None
        assert mock_streamlit.session_state['analysis_results'] is None
        
    def test_render_header(self, app, mock_streamlit):
        """Header render testi"""
        app.render_header()
        
        # st.markdown çağrılarını kontrol et
        assert mock_streamlit.markdown.call_count >= 2
        
    def test_mysql_connection_success(self, app, mock_streamlit, mock_engine):
        """MySQL bağlantı başarı testi"""
        with patch('streamlit_app.create_engine', return_value=mock_engine):
            with patch('streamlit_app.EXPLORER_AVAILABLE', True):
                with patch('streamlit_app.DataExplorer') as mock_explorer:
                    
                    # Form submit simülasyonu
                    mock_streamlit.form.return_value.__enter__.return_value.text_input.side_effect = [
                        'localhost',  # host
                        'testdb',     # database
                        'user',       # username
                        'pass'        # password
                    ]
                    mock_streamlit.form.return_value.__enter__.return_value.number_input.return_value = 3306
                    mock_streamlit.form.return_value.__enter__.return_value.form_submit_button.return_value = True
                    
                    app._render_mysql_connection()
                    
                    # Başarılı bağlantı kontrolü
                    assert app.engine == mock_engine
                    assert app.connection_status is True
                    assert mock_streamlit.session_state['connection_established'] is True
                    mock_streamlit.success.assert_called_once()
                    
    def test_mysql_connection_failure(self, app, mock_streamlit):
        """MySQL bağlantı hata testi"""
        with patch('streamlit_app.create_engine', side_effect=Exception("Connection failed")):
            
            # Form submit simülasyonu
            mock_streamlit.form.return_value.__enter__.return_value.text_input.side_effect = [
                'localhost',  # host
                'testdb',     # database
                'user',       # username
                'pass'        # password
            ]
            mock_streamlit.form.return_value.__enter__.return_value.number_input.return_value = 3306
            mock_streamlit.form.return_value.__enter__.return_value.form_submit_button.return_value = True
            
            app._render_mysql_connection()
            
            # Hata kontrolü
            assert app.connection_status is False
            assert mock_streamlit.session_state['connection_established'] is False
            mock_streamlit.error.assert_called_once()
            
    def test_sqlite_connection_success(self, app, mock_streamlit, mock_engine):
        """SQLite bağlantı başarı testi"""
        with patch('streamlit_app.create_engine', return_value=mock_engine):
            with patch('streamlit_app.EXPLORER_AVAILABLE', True):
                with patch('streamlit_app.DataExplorer') as mock_explorer:
                    
                    # Form submit simülasyonu
                    mock_streamlit.form.return_value.__enter__.return_value.text_input.return_value = './test.db'
                    mock_streamlit.form.return_value.__enter__.return_value.form_submit_button.return_value = True
                    
                    app._render_sqlite_connection()
                    
                    # Başarılı bağlantı kontrolü
                    assert app.engine == mock_engine
                    assert app.connection_status is True
                    assert mock_streamlit.session_state['connection_established'] is True
                    mock_streamlit.success.assert_called_once()
                    
    def test_postgresql_connection_success(self, app, mock_streamlit, mock_engine):
        """PostgreSQL bağlantı başarı testi"""
        with patch('streamlit_app.create_engine', return_value=mock_engine):
            with patch('streamlit_app.EXPLORER_AVAILABLE', True):
                with patch('streamlit_app.DataExplorer') as mock_explorer:
                    
                    # Form submit simülasyonu
                    mock_streamlit.form.return_value.__enter__.return_value.text_input.side_effect = [
                        'localhost',  # host
                        'testdb',     # database
                        'user',       # username
                        'pass'        # password
                    ]
                    mock_streamlit.form.return_value.__enter__.return_value.number_input.return_value = 5432
                    mock_streamlit.form.return_value.__enter__.return_value.form_submit_button.return_value = True
                    
                    app._render_postgresql_connection()
                    
                    # Başarılı bağlantı kontrolü
                    assert app.engine == mock_engine
                    assert app.connection_status is True
                    assert mock_streamlit.session_state['connection_established'] is True
                    mock_streamlit.success.assert_called_once()
                    
    def test_render_main_content_no_connection(self, app, mock_streamlit):
        """Bağlantı yokken ana içerik testi"""
        mock_streamlit.session_state['connection_established'] = False
        
        app.render_main_content()
        
        mock_streamlit.info.assert_called_once()
        
    def test_render_main_content_with_connection(self, app, mock_streamlit, mock_engine):
        """Bağlantı varken ana içerik testi"""
        app.engine = mock_engine
        mock_streamlit.session_state['connection_established'] = True
        
        # Inspector mock'u
        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = ['table1', 'table2']
        
        with patch('streamlit_app.sa.inspect', return_value=mock_inspector):
            with patch.object(app, '_analyze_table') as mock_analyze:
                
                mock_streamlit.selectbox.return_value = 'table1'
                
                app.render_main_content()
                
                mock_streamlit.selectbox.assert_called()
                mock_analyze.assert_called_once_with('table1')
                
    def test_analyze_table_success(self, app, mock_streamlit, mock_engine):
        """Tablo analizi başarı testi"""
        app.engine = mock_engine
        
        # Explorer mock'u
        mock_explorer = Mock()
        mock_explorer.analyze_table.return_value = {
            'columns': [
                {
                    'name': 'id',
                    'type': 'INTEGER',
                    'null_rate': 0.0,
                    'unique_count': 100,
                    'is_text': False,
                    'sample_values': [1, 2, 3, 4, 5]
                },
                {
                    'name': 'text',
                    'type': 'TEXT',
                    'null_rate': 0.1,
                    'unique_count': 50,
                    'is_text': True,
                    'shortest_text': 'a',
                    'longest_text': 'very long text',
                    'sample_values': ['text1', 'text2', 'text3'],
                    'most_common_words': [('test', 10), ('text', 8)]
                }
            ],
            'row_count': 100
        }
        app.explorer = mock_explorer
        
        app._analyze_table('test_table')
        
        mock_explorer.analyze_table.assert_called_once_with('test_table')
        assert mock_streamlit.subheader.call_count >= 2
        
    def test_analyze_table_error(self, app, mock_streamlit, mock_engine):
        """Tablo analizi hata testi"""
        app.engine = mock_engine
        
        # Explorer mock'u
        mock_explorer = Mock()
        mock_explorer.analyze_table.side_effect = Exception("Analysis failed")
        app.explorer = mock_explorer
        
        app._analyze_table('test_table')
        
        mock_streamlit.error.assert_called_once()
        
    def test_render_ai_analysis_no_ai_helper(self, app, mock_streamlit):
        """AI Helper yokken AI analizi testi"""
        with patch('streamlit_app.AI_HELPER_AVAILABLE', False):
            app._render_ai_analysis('test_table')
            
            mock_streamlit.error.assert_called_once()
            
    def test_render_ai_analysis_with_ai_helper(self, app, mock_streamlit, sample_dataframe):
        """AI Helper ile AI analizi testi"""
        with patch('streamlit_app.AI_HELPER_AVAILABLE', True):
            with patch('streamlit_app.AIHelper') as mock_ai_helper_class:
                
                # AI Helper mock'u
                mock_ai_helper = Mock()
                mock_ai_helper.summarize_texts.return_value = {
                    'summary': 'Bu bir test özetidir.',
                    'word_count': 100
                }
                mock_ai_helper_class.return_value = mock_ai_helper
                app.ai_helper = mock_ai_helper
                
                # Session state ayarla
                mock_streamlit.session_state['table_data'] = sample_dataframe
                mock_streamlit.session_state['ai_model'] = 'openai'
                mock_streamlit.session_state['ai_action'] = 'Özetleme'
                
                # Multiselect mock'u
                mock_streamlit.multiselect.return_value = ['text']
                
                # Button click simülasyonu
                mock_streamlit.button.return_value = True
                
                app._render_ai_analysis('test_table')
                
                # AI analizi çağrıldı mı kontrol et
                mock_ai_helper.summarize_texts.assert_called_once()
                mock_streamlit.success.assert_called_once()
                
    def test_render_ai_analysis_different_actions(self, app, mock_streamlit, sample_dataframe):
        """Farklı AI işlemleri testi"""
        with patch('streamlit_app.AI_HELPER_AVAILABLE', True):
            with patch('streamlit_app.AIHelper') as mock_ai_helper_class:
                
                # AI Helper mock'u
                mock_ai_helper = Mock()
                mock_ai_helper.classify_texts.return_value = {
                    'classifications': [
                        {'text': 'test1', 'category': 'A', 'confidence': 0.9},
                        {'text': 'test2', 'category': 'B', 'confidence': 0.8}
                    ]
                }
                mock_ai_helper.cluster_texts.return_value = {
                    'clusters': [
                        ['test1', 'test2'],
                        ['test3', 'test4']
                    ]
                }
                mock_ai_helper.analyze_trends.return_value = {
                    'trends': {
                        'trend1': 'Artış trendi',
                        'trend2': 'Azalış trendi'
                    }
                }
                mock_ai_helper_class.return_value = mock_ai_helper
                app.ai_helper = mock_ai_helper
                
                # Session state ayarla
                mock_streamlit.session_state['table_data'] = sample_dataframe
                mock_streamlit.multiselect.return_value = ['text']
                mock_streamlit.button.return_value = True
                
                # Farklı AI işlemlerini test et
                actions = ['Sınıflandırma', 'Kümelendirme', 'Trend Analizi']
                
                for action in actions:
                    mock_streamlit.session_state['ai_action'] = action
                    app._render_ai_analysis('test_table')
                    
                # Her işlem için ilgili fonksiyon çağrıldı mı kontrol et
                mock_ai_helper.classify_texts.assert_called_once()
                mock_ai_helper.cluster_texts.assert_called_once()
                mock_ai_helper.analyze_trends.assert_called_once()
                
    def test_render_footer(self, app, mock_streamlit):
        """Footer render testi"""
        app.render_footer()
        
        mock_streamlit.markdown.assert_called()
        
    def test_cache_integration(self, app, mock_streamlit):
        """Cache entegrasyonu testi"""
        with patch('streamlit_app.CACHE_AVAILABLE', True):
            with patch('streamlit_app.EmbeddingCache') as mock_cache_class:
                
                # Cache mock'u
                mock_cache = Mock()
                mock_cache.get_cache_stats.return_value = {
                    'cache_size': 100,
                    'hit_rate': 85.5
                }
                mock_cache_class.return_value = mock_cache
                
                # Cache temizleme butonu
                mock_streamlit.button.return_value = True
                
                # Sidebar cache bölümünü test et
                with patch.object(app, '_render_mysql_connection'):
                    app.render_sidebar()
                    
                mock_cache.get_cache_stats.assert_called_once()
                mock_streamlit.metric.assert_called()
                
    def test_metrics_integration(self, app, mock_streamlit):
        """Metrik entegrasyonu testi"""
        with patch('streamlit_app.METRICS_AVAILABLE', True):
            with patch('streamlit_app.get_metrics_summary') as mock_get_metrics:
                
                # Metrik mock'u
                mock_get_metrics.return_value = {
                    'stats': {
                        'total_calls': 50,
                        'total_tokens': 1000
                    }
                }
                
                # Metrik sıfırlama butonu
                mock_streamlit.button.return_value = True
                
                # Sidebar metrik bölümünü test et
                with patch.object(app, '_render_mysql_connection'):
                    app.render_sidebar()
                    
                mock_get_metrics.assert_called_once()
                mock_streamlit.metric.assert_called()
                
    def test_error_handling(self, app, mock_streamlit):
        """Hata yönetimi testi"""
        # Genel hata durumları için test
        with patch('streamlit_app.EXPLORER_AVAILABLE', True):
            with patch('streamlit_app.DataExplorer', side_effect=Exception("Explorer error")):
                
                app.engine = Mock()
                mock_streamlit.session_state['connection_established'] = True
                
                app.render_main_content()
                
                mock_streamlit.error.assert_called()

if __name__ == "__main__":
    pytest.main([__file__]) 