import sys
from bson import ObjectId
from flask import Flask, jsonify, request
from flask_restful import Resource, Api, reqparse
import requests
from pymongo import MongoClient

app = Flask(__name__)
api = Api(app)

# Connect to MongoDB
client = MongoClient('mongodb://mongo:27017/')
db = client['booksdb']
bookscoll = db['books']
ratingscoll = db['ratings']

# POST adds a book to /books and returns the string id for the newly created book record
@app.route('/books', methods=['POST'])
def post_book():
    content_type = request.headers.get('Content-Type')
    if content_type != 'application/json':
        return {"error": "Expected 'application/json' content_type"}, 415  # 415 Unsupported Media Type

    try:
        data = request.get_json()
        book_title = data["title"]
        book_isbn = data["ISBN"]
        book_genre = data["genre"]
    except KeyError:
        print("POST /books exception: required parameters not supplied")
        sys.stdout.flush()
        return {"error": "Required parameters not supplied"}, 422

    if book_genre not in ['Fiction', 'Children', 'Biography', 'Science', 'Science Fiction', 'Fantasy', 'Other']:
        return {"error": "Invalid Genre"}, 422

    book = bookscoll.find_one({"ISBN": book_isbn})
    if book is not None:
        print(f"{book_isbn} already exists in Mongo with key {str(book['_id'])}")
        return f"{book_isbn} already exists in Mongo with key {str(book['_id'])}", 404

    google_books_url = f'https://www.googleapis.com/books/v1/volumes?q=isbn:{book_isbn}'
    response = requests.get(google_books_url)

    try:
        google_books_data = response.json()['items'][0]['volumeInfo']
    except KeyError:
        if response.json().get('totalItems') == 0:
            return {"error": "Invalid ISBN number"}, 400
        return {"error": "Unable to connect to Google"}, 500

    book_publisher = google_books_data.get('publisher', 'missing')
    book_authors = google_books_data.get('authors', ['missing'])
    if book_authors:
        book_authors = " and ".join(book_authors) if len(book_authors) > 1 else book_authors[0]
    book_publishedDate = google_books_data.get('publishedDate', 'missing')
    if book_publishedDate:
        try:
            from datetime import datetime
            datetime.strptime(book_publishedDate, '%Y-%m-%d')
        except ValueError:
            book_publishedDate = book_publishedDate[:4] if len(book_publishedDate) >= 4 else 'missing'


    result = bookscoll.insert_one({'title': book_title, 'authors': book_authors, 'ISBN': book_isbn, 'publisher': book_publisher, 'publishedDate': book_publishedDate, 'genre': book_genre})
    ratingscoll.insert_one({'_id': result.inserted_id, 'values': [], 'average': 0.0, 'title': book_title})
    
    print(f"Inserted {book_title} into mongo with ID {str(result.inserted_id)}")
    return {"ID": str(result.inserted_id)}, 201

# GET returns all the books in the collection in json that match the requested query string
@app.route('/books', methods=['GET'])
def get_books():
    query = request.args.to_dict()
    books = list(bookscoll.find(query))
    for book in books:
        book['_id'] = str(book['_id'])
    return jsonify(books), 200

# GET retrieves a specific book from the collection
@app.route('/books/<string:id>', methods=['GET'])
def get_book(id):
    book = bookscoll.find_one({'_id': ObjectId(id)})
    if book:
        book['_id'] = str(book['_id'])
        return jsonify(book), 200
    return {"error": "book with ID '" + str(id)  + "' was not found"}, 404

# DELETE deletes a book from the collection
@app.route('/books/<string:id>', methods=['DELETE'])
def delete_book(id):
    result = bookscoll.delete_one({'_id': ObjectId(id)})
    ratingscoll.delete_one({'_id': ObjectId(id)})
    if result.deleted_count > 0:
        return {"ID": str(id)}, 200
    return {"error": "book with ID '" + str(id)  + "' was not found"}, 404

# PUT modifies a book associated with the given id
@app.route('/books/<string:id>', methods=['PUT'])
def put_book(id):
    if not bookscoll.find_one({'_id': ObjectId(id)}):
        return {"error": "book with ID '" + str(id)  + "' was not found"}, 404
    
    if not request.is_json:
        return {"error": "Unsupported media type"}, 415

    try:
        data = request.get_json()
        book_title = data["title"]
        book_isbn = data["ISBN"]
        book_genre = data["genre"]
        book_authors = data["authors"]
        book_publisher = data["publisher"]
        book_publishedDate = data["publishedDate"]
    except KeyError:
        return {"error": "Required parameters not supplied"}, 422

    if book_genre not in ['Fiction', 'Children', 'Biography', 'Science', 'Science Fiction', 'Fantasy', 'Other']:
        return {"error": "Invalid Genre"}, 422

    update_data = {
        'title': book_title,
        'ISBN': book_isbn,
        'genre': book_genre,
        'authors': book_authors,
        'publisher': book_publisher,
        'publishedDate': book_publishedDate
    }
    
    bookscoll.update_one({'_id': id}, {'$set': update_data})
    return {"ID": str(id)}, 200

# GET returns a JSON array containing the information /ratings/{id} for each book, or for a specific book id
@app.route('/ratings', methods=['GET'])
def get_ratings():
    query = request.args.to_dict()
    ratings = list(ratingscoll.find(query))
    for rating in ratings:
        rating['_id'] = str(rating['_id'])
    return jsonify(ratings), 200

# GET returns the JSON structure for the given id
@app.route('/ratings/<string:id>', methods=['GET'])
def get_rating(id):
    rating = ratingscoll.find_one({'_id': ObjectId(id)})
    if rating:
        rating['_id'] = str(rating['_id'])
        return jsonify(rating), 200
    return {"error": "book with ID '" + str(id)  + "' not found"}, 404

# POST adds a new rating for the book of the given id and returns the new average rating for the book
@app.route('/ratings/<string:id>/values', methods=['POST'])
def post_rating_value(id):
    if not ratingscoll.find_one({'_id': ObjectId(id)}):
        return {"error": "book with ID '" + str(id)  + "' not found"}, 404
    try:
        data = request.get_json()
        value = data['value']
    except KeyError:
        return {"error": "Required parameters not supplied"}, 422

    if value not in range(1, 6):
        return {"error": "Invalid Value"}, 422

    rating = ratingscoll.find_one({'_id': ObjectId(id)})
    values = rating['values']
    values.append(value)
    average = round(float(sum(values) / len(values)), 2)

    ratingscoll.update_one({'_id': ObjectId(id)}, {'$set': {'values': values, 'average': average}})
    return {"rating average": str(average)}, 200

# GET returns a json array containing the top 3 books with the highest ratings
@app.route('/top', methods=['GET'])
def get_top_ratings():
    ratings = list(ratingscoll.find({'values.2': {'$exists': True}}))
    ratings.sort(key=lambda x: x['average'], reverse=True)
    top_ratings = ratings[:3]
    third_rating = top_ratings[2]['average'] if len(top_ratings) == 3 else None
    if third_rating:
        for rating in ratings[3:]:
            if rating['average'] < third_rating:
                break
            top_ratings.append(rating)
    for rating in top_ratings:
        rating['_id'] = str(rating['_id'])
    return jsonify(top_ratings), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
