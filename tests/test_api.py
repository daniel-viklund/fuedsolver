from fastapi.testclient import TestClient
from backend.app import app

client=TestClient(app)

def test_health_and_website():
    assert client.get('/api/health').json()['engine_ready']
    assert 'Feudsolver' in client.get('/').text

def test_reject_invalid_board_and_unknown_ocr_tile():
    assert client.post('/api/solve',json={'board':[],'rack':'A'}).status_code==422
    board=['.'*15]*15;board[7]='.......?.......'
    assert client.post('/api/solve',json={'board':board,'rack':'A'}).status_code==422

def test_reject_invalid_image():
    response=client.post('/api/recognize',files={'image':('test.png',b'not an image','image/png')})
    assert response.status_code==422

def test_solve_with_installed_dictionary():
    response=client.post('/api/solve',json={'board':['.'*15]*15,'rack':'ÖL'})
    assert response.status_code==200
    assert any(move['word']=='ÖL' for move in response.json()['moves'])
