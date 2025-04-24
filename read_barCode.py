from pyzbar.pyzbar import decode
from PIL import Image

def extract_barcode(image_path):
    image = Image.open(image_path)
    decoded_objects = decode(image)

    for obj in decoded_objects:
        if obj.type in ['EAN13', 'ISBN13', 'QRCODE']:
            isbn = obj.data.decode('utf-8')
            return isbn
    return None #this is not a valid isbn code

import requests

def fetch_book_info(isbn):
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    response = requests.get(url)
    
    if response.status_code != 200:
        return {"error": "Failed to fetch data"}
    
    data = response.json()
    
    if "items" not in data or not data["items"]:
        return {"error": "No book found for this ISBN"}
    
    book = data["items"][0]["volumeInfo"]

    return {
        "title": book.get("title"),
        "authors": book.get("authors", []),
        "description": book.get("description"),
        "thumbnail": book.get("imageLinks", {}).get("thumbnail"),
        "publishedDate": book.get("publishedDate")
    }


# Example usage
#isbn1 = extract_barcode("test_barcode.jpeg")
#isbn2 = extract_barcode("cook_book.jpg")
isbn3 = extract_barcode("japanese_book.jpg")
info = fetch_book_info(isbn3)
print(info)
#print("Detected ISBN:", isbn1)
#print("Detected ISBN:", isbn2)
#print("Detected ISBN:", isbn3)
