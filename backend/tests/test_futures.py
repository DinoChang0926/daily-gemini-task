import pytest
import pandas as pd
from data_modules.futures import get_futures_info

def test_get_futures_info_success(mocker):
    # Mock FinMind Data
    mock_df = pd.DataFrame({
        'date': ['2024-01-26', '2024-01-26'],
        'futures_id': ['CDF', 'CDF'], 
        'close': [630, 640],
        'open_interest': [2000, 2010],
        'volume': [100, 500] 
    })
    
    # Mock DataLoader
    mock_dl = mocker.patch('data_modules.futures.DataLoader')
    mock_instance = mock_dl.return_value
    mock_instance.taiwan_futures_daily.return_value = mock_df
    
    # Mock futures_mapping
    mocker.patch('data_modules.futures.futures_mapping.get_futures_id', return_value="CDF")
    
    # Act
    result = get_futures_info("2330")
    
    # Assert
    assert result["futures_id"] == 'CDF'
    assert result["close"] == 640.0
    assert result["open_interest"] == 2010

def test_get_futures_info_no_mapping(mocker):
    # Mock futures_mapping return None
    mocker.patch('data_modules.futures.futures_mapping.get_futures_id', return_value=None)
    
    result = get_futures_info("0000")
    assert result["futures_id"] is None
