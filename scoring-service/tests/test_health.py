from app.main import health

def test_health_is_unhealthy_without_a_model():
    response = health()
    assert response.status_code == 503
    assert response.body == b'{"status":"unhealthy","modelLoaded":false}'
