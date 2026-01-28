import pytest
import requests
from data_modules.chips import get_twse_chips

def test_get_twse_chips_success(mocker):
    # Mock T86 Response (投信)
    mock_t86 = {
        "stat": "OK",
        "data": [
            ["2330", "台積電", "100", "50", "150", "200", "0", "0", "10,000", "5,000", "5,000", "0", "0", "0", "0", "0"]
        ]
    }
    
    # Mock MI_MARGN Response (融資)
    mock_margin = {
        "stat": "OK",
        "tables": [{
            "data": [
                ["2330", "台積電", "100", "50", "0", "1,000", "1,200", "0", "0", "0", "0", "0", "0", "0", "0"]
            ]
        }]
    }

    def mock_get(url, *args, **kwargs):
        class MockResponse:
            def __init__(self, json_data, status_code):
                self.json_data = json_data
                self.status_code = status_code
            def json(self):
                return self.json_data
        
        if "T86" in url:
            return MockResponse(mock_t86, 200)
        elif "MI_MARGN" in url:
            return MockResponse(mock_margin, 200)
        return MockResponse({}, 404)

    mocker.patch('requests.get', side_effect=mock_get)

    result = get_twse_chips("20240126", "2330")
    
    assert result["it_buy"] == 10000
    assert result["it_sell"] == 5000
    assert result["it_net"] == 5000
    assert result["margin_balance"] == 1200
    assert result["margin_prev_balance"] == 1000
    assert result["margin_diff"] == 200

def test_get_twse_chips_not_found(mocker):
    mocker.patch('requests.get', return_value=mocker.Mock(status_code=200, json=lambda: {"stat": "OK", "data": []}))
    
    result = get_twse_chips("20240126", "9999")
    assert result["it_net"] == 0
    assert result["margin_diff"] == 0
