import requests
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:5000"

# Default test credentials
USERNAME = "testuser"
PASSWORD = "password123"
TEST_ISBN = "9781449331818"  # Example ISBN: Learning JavaScript Design Patterns

# Create a session to maintain login
session = requests.Session()

def login():
    print("Logging in...")
    login_page = session.get(f"{BASE_URL}/login")
    soup = BeautifulSoup(login_page.text, "html.parser")
    
    # Submit login form
    response = session.post(f"{BASE_URL}/login", data={
        "username": USERNAME,
        "password": PASSWORD
    })

    return "Logout" in response.text  # Checks if logged in

def add_book():
    print("Adding book...")
    response = session.post(f"{BASE_URL}/add_book", data={"isbn": TEST_ISBN}, allow_redirects=True)
    return "added successfully" in response.text or "already in your catalogue" in response.text

def verify_book_added():
    print("Verifying book is listed...")
    response = session.get(f"{BASE_URL}/")
    return TEST_ISBN in response.text or "Learning JavaScript Design Patterns" in response.text

def logout():
    print("Logging out...")
    response = session.get(f"{BASE_URL}/logout")
    return "Login" in response.text

def run_tests():
    if not login():
        print("❌ Login failed")
        return
    print("✅ Login successful")

    if add_book():
        print("✅ Book add request successful")
    else:
        print("❌ Failed to add book")

    if verify_book_added():
        print("✅ Book appears in catalogue")
    else:
        print("❌ Book not found in catalogue")

    if logout():
        print("✅ Logout successful")
    else:
        print("❌ Logout failed")

if __name__ == "__main__":
    run_tests()
