import sys

import connectionController
from assertions import *

book1 = {
    "title":"Adventures of Huckleberry Finn", 
    "ISBN":"9780520343641", 
    "genre":"Fiction"
}

book2 = {
    "title":"The Best of Isaac Asimov", 
    "ISBN":"9780385050784", 
    "genre":"Science Fiction"
} 

book3 = {
    "title":"Fear No Evil", 
    "ISBN":"9780394558783", 
    "genre":"Biography"
}

book4 = {
    "title": "No such book", 
    "ISBN":"0000001111111", 
    "genre":"Biography"
}

book5 = {
    "title":"The Greatest Joke Book Ever", 
    "authors":"Mel Greene", "ISBN":"9780380798490", 
    "genre":"Jokes"
}

Book6 = {
    "title":"The Adventures of Tom Sawyer", 
    "ISBN":"9780195810400", 
    "genre":"Fiction"
}

book7 = {
    "title": "I, Robot", 
    "ISBN":"9780553294385", 
    "genre":"Science Fiction"
}

book8 = {
    "title": "Second Foundation", 
    "ISBN":"9780553293364", 
    "genre":"Science Fiction"
}

book_collection = {}

def test_post_books():
    response_1 = connectionController.http_post("books", book1)
    response_2 = connectionController.http_post("books", book2)
    response_3 = connectionController.http_post("books", book3)

    assert response_1.status_code == 201
    assert response_2.status_code == 201
    assert response_3.status_code == 201

    id_1 = response_1.json()["ID"]
    id_2 = response_2.json()["ID"]
    id_3 = response_3.json()["ID"]

    book_collection[2] = id_2

    assert id_1 != id_2 and id_2 != id_3 and id_1 != id_3

def test_get_book_by_id():
    response = connectionController.http_get_qs("books", book1["ISBN"])
    book_id = response.json()[0]["_id"]
    response = connectionController.http_get(f'books/{str(book_id)}')
    assert_status_code(response, 200)
    assert response.json()["authors"] == "Mark Twain"

def test_get_books():
    response = connectionController.http_get("books")
    assert_status_code(response, 200)
    assert len(response.json()) == 3

def test_post_invalid_isbn():
    response = connectionController.http_post("books", book4)
    assert response.status_code in [400, 500]

def test_delete_books():
    response = connectionController.http_get_qs("books", book2["ISBN"])
    book_id = response.json()[0]["_id"]
    response = connectionController.http_delete(f'books/{str(book_id)}')
    assert_status_code(response, 200)

def test_get_deleted_book():
    response = connectionController.http_get(f'books/{book_collection[2]}')
    assert_status_code(response, 404)

def test_post_invalid_genre():
    response = connectionController.http_post("books", book5)
    assert_status_code(response, 422)