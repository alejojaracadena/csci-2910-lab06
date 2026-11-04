import pytest

def test_get_seeded_artwork(client, seeded_db):
    # Arrange: seeded_db has already loaded the 11 artworks (the Mona Lisa is first)
    expected = {"id": 1, **seeded_db[0]}

    # Act
    response = client.get("/artworks/1")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected

@pytest.mark.parametrize(
    "method, use_body",
    [
        ("get", False),
        ("put", True),
        ("delete", False),
    ],
    ids=["get", "put", "delete"],
)
def test_artwork_not_found(client, sample_artwork, method, use_body):
    kwargs = {"json": sample_artwork} if use_body else {}
    response = client.request(method, "/artworks/9999", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Artwork not found"}

def test_non_integer_id(client):
    response = client.get("/artworks/mona-lisa")
    assert response.status_code == 422

def test_list_artworks_empty(client):
    expected = []

    response = client.get("/artworks/")

    assert response.status_code == 200
    assert response.json() == expected

def test_create_artwork(client, sample_artwork):
    response = client.post("/artworks/", json=sample_artwork)
    body = response.json()

    assert response.status_code == 201
    assert isinstance(body["id"], int)
    for key, value in sample_artwork.items():
        assert body[key] == value

def test_create_duplicate(client, sample_artwork, created_artwork):
    response = client.post(f"/artworks/", json=sample_artwork)
    assert response.status_code == 409
    assert response.json() == {'detail':"An artwork with that title and artist already exists"}

def test_create_duplicate_ignores_case(client, sample_artwork, created_artwork):
    body = {**sample_artwork, 
            'title': sample_artwork['title'].upper(), 
            'artist': sample_artwork['artist'].lower()
            }
    response = client.post('/artworks/', json=body)
    
    assert response.status_code == 409
    assert response.json() == {'detail':"An artwork with that title and artist already exists"}

def test_update_into_duplicate(client, seeded_db):
    body = {**seeded_db[1], 
            'title': seeded_db[0]['title'],
            'artist': seeded_db[0]['artist']
            }
    response = client.put("/artworks/2", json=body)
    assert response.status_code == 409

    check = client.get("/artworks/2")
    assert check.json() == {'id':2, **seeded_db[1]}

def test_update_same_title_and_artist_is_allowed(client, created_artwork, sample_artwork):
    body = {**sample_artwork,
            "museum": "a diff museum"}
    response = client.put(f"/artworks/{created_artwork['id']}", json=body)

    assert response.status_code == 200

def test_create_artwork_is_saved(client, created_artwork):

    response = client.get(f"/artworks/{created_artwork['id']}")

    assert response.status_code == 200
    assert created_artwork == response.json()

def test_update_artwork(client,created_artwork, updated_artwork):
    expected = {"id": created_artwork['id'], **updated_artwork}
    
    P_response = client.put(f"/artworks/{created_artwork['id']}", json=updated_artwork)

    assert P_response.status_code == 200
    assert P_response.json() == expected

    G_response = client.get(f"/artworks/{created_artwork['id']}")

    assert G_response.status_code == 200
    assert G_response.json() == expected

def test_delete_artwork(client, created_artwork):

    response = client.delete(f"/artworks/{created_artwork['id']}")

    assert response.status_code == 204
    assert response.content == b""

    Not_found_check = client.get(f"/artworks/{created_artwork['id']}")
    assert Not_found_check.status_code == 404

@pytest.mark.parametrize(
    "missing_field",
    ["title", "artist", "year", "medium", "museum", "image_url"],
)
def test_create_missing_field(client, sample_artwork, missing_field):
    body = {}
    for key, value in sample_artwork.items():
        if key != missing_field:
            body[key] = value

    response = client.post("/artworks/", json=body)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", missing_field]

@pytest.mark.parametrize(
    "field, bad_value",
    [("year", 3000), ("year", "el futuro"), ("title", "")]
)
def test_create_invalid_value(client, sample_artwork, field, bad_value):
    body = {**sample_artwork, field: bad_value}

    response = client.post("/artworks/", json=body)

    assert response.status_code == 422

@pytest.mark.parametrize(
    "params, expected",
    [({"limit": 0}, 0), ({"skip": 100}, 0), #potential fails
     ({"limit": 3}, 3), ({"skip": 9}, 2)]
)
def test_pagination_counts(client, seeded_db, params, expected):
    response = client.get("/artworks/", params=params)
    assert response.status_code == 200
    assert len(response.json()) == expected

@pytest.mark.parametrize(
    "params",
        [({"limit": 101}), ({"skip": -1})]
)
def test_pagination_invalid(client, seeded_db, params):
    response = client.get("/artworks/", params=params)
    assert response.status_code == 422

@pytest.mark.parametrize(
    "artist, expected_titles",
    [("Claude Monet", ["Impression, Sunrise", "Woman with a Parasol – Madame Monet and Her Son"]),
     ("da vinci", ["Mona Lisa", "Lady with an Ermine"]),
     ("DaBaby", [])],
     ids=["exact", "lowercase", "no_exist"]
)
def test_filter_by_artist(client, seeded_db, artist, expected_titles):
    response = client.get("/artworks/", params={"artist" : artist})

    assert response.status_code == 200

    assert [a["title"] for a in response.json()] == expected_titles