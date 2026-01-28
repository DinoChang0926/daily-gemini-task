import pytest
from data_modules.cb import get_cb_info

def test_get_cb_info_success(mocker):
    mock_response = {
        "aaData": [
            ["47631", "材料一", "100", "0", "0"],
            ["47632", "材料二", "120", "0", "0"],
            ["23301", "台積一", "500", "0", "0"]
        ]
    }
    
    mocker.patch('requests.get', return_value=mocker.Mock(status_code=200, json=lambda: mock_response))
    
    # 測試材料 (4763)
    result = get_cb_info("4763", current_price=110)
    assert result["has_cb"] is True
    assert len(result["cb_list"]) == 2
    # 47631: (110 - 100) / 100 * 100% = 10%
    assert result["cb_list"][0]["deviation_rate"] == 10.0
    # 47632: (110 - 120) / 120 * 100% = -8.33
    assert result["cb_list"][1]["deviation_rate"] == -8.33

def test_get_cb_info_none(mocker):
    mocker.patch('requests.get', return_value=mocker.Mock(status_code=200, json=lambda: {"aaData": []}))
    result = get_cb_info("2330")
    assert result["has_cb"] is False
    assert len(result["cb_list"]) == 0
