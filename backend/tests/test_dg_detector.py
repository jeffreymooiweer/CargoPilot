from app.services.dg.detector import detect_dangerous_goods, detect_un_numbers


def test_detects_un_numbers():
    assert detect_un_numbers("Benzine UN 1203 in vaten") == ["1203"]
    assert detect_un_numbers("UN1203 en ID 8000") == ["1203", "8000"]
    assert detect_un_numbers("Gewone lading") == []


def test_detect_dangerous_goods_flag_and_message():
    dangerous, messages = detect_dangerous_goods("Accu's UN 3480")
    assert dangerous is True
    assert messages == ["dg_un_detected"]

    dangerous, messages = detect_dangerous_goods("Stalen balk HEA200")
    assert dangerous is False
    assert messages == []
