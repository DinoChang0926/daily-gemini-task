import pytest
import pandas as pd
from utils.ticker_utils import get_ticker_by_name
from utils import ticker_utils

@pytest.fixture
def mock_stock_info():
    data = {
        'stock_id': ['2330', '8299', '2317'],
        'stock_name': ['台積電', '欣銓', '鴻海'],
        'type': ['twse', 'tpex', 'twse']
    }
    return pd.DataFrame(data)

def test_get_ticker_by_name_success(mocker, mock_stock_info):
    # 重設快取
    ticker_utils.CACHED_STOCK_INFO = None
    
    # Mock DataLoader
    mock_dl = mocker.patch('utils.ticker_utils.DataLoader')
    mock_instance = mock_dl.return_value
    mock_instance.taiwan_stock_info.return_value = mock_stock_info
    
    # 測試上市股票
    assert get_ticker_by_name("台積電") == "2330.TW"
    
    # 測試上櫃股票
    assert get_ticker_by_name("欣銓") == "8299.TWO"

def test_get_ticker_by_name_not_found(mocker, mock_stock_info):
    ticker_utils.CACHED_STOCK_INFO = mock_stock_info
    
    result = get_ticker_by_name("不存在的股票")
    assert result == "【資料不足，無法確認】"

def test_get_ticker_by_name_exception(mocker):
    ticker_utils.CACHED_STOCK_INFO = None
    mock_dl = mocker.patch('utils.ticker_utils.DataLoader')
    mock_dl.side_effect = Exception("API Error")
    
    result = get_ticker_by_name("台積電")
    assert "【查詢發生錯誤: API Error】" in result
