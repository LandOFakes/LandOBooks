from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
import requests
from models import db, User, Book

# App Configuration 
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_here' # Change this!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database and Login Manager Initialization 
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to 'login' view if @login_required fails

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper Functions 
def get_book_details_from_google(isbn):
    """Fetches book details from Google Books API."""
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors
        data = response.json()

        if data.get("totalItems", 0) > 0 and "items" in data:
            item = data["items"][0] # Use the first result
            volume_info = item.get("volumeInfo", {})

            title = volume_info.get("title", "N/A")
            authors = ", ".join(volume_info.get("authors", ["N/A"]))
            page_count = volume_info.get("pageCount")
            average_rating = volume_info.get("averageRating")
            thumbnail_url = volume_info.get("imageLinks", {}).get("thumbnail")

            return {
                "isbn": isbn,
                "title": title,
                "authors": authors,
                "page_count": page_count,
                "average_rating": average_rating,
                "thumbnail_url": thumbnail_url
            }
        else:
            return None # Book not found or no items
    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        return {"error": f"Could not connect to Google Books API: {e}"}
    except ValueError as e: # Includes JSONDecodeError
        print(f"JSON Parsing Error: {e}")
        return {"error": "Error parsing response from Google Books API."}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"error": "An unexpected error occurred while fetching book data."}


# Routes 
@app.route('/')
@login_required
def index():
    user_books = Book.query.filter_by(user_id=current_user.id).order_by(Book.title).all()
    return render_template('index.html', books=user_books)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/add_book', methods=['POST'])
@login_required
def add_book():
    isbn = request.form.get('isbn')
    if not isbn:
        flash('ISBN is required.', 'warning')
        return redirect(url_for('index'))

    # Check if book already exists for this user by ISBN (if provided)
    if isbn:
        existing_book = Book.query.filter_by(user_id=current_user.id, isbn=isbn).first()
        if existing_book:
            flash(f'Book with ISBN {isbn} already in your catalogue.', 'info')
            return redirect(url_for('index'))

    book_data = get_book_details_from_google(isbn)

    if book_data and "error" not in book_data:
        new_book = Book(
            isbn=book_data.get("isbn"),
            title=book_data.get("title", "Unknown Title"),
            authors=book_data.get("authors"),
            page_count=book_data.get("page_count"),
            average_rating=book_data.get("average_rating"),
            thumbnail_url=book_data.get("thumbnail_url"),
            user_id=current_user.id
        )
        db.session.add(new_book)
        db.session.commit()
        flash(f'Book "{new_book.title}" added successfully!', 'success')
    elif book_data and "error" in book_data:
        flash(f'Error adding book: {book_data["error"]}', 'danger')
    else:
        flash(f'Book with ISBN {isbn} not found or error fetching data.', 'warning')

    return redirect(url_for('index'))


@app.route('/delete_book/<int:book_id>', methods=['POST']) # Use POST for deletion
@login_required
def delete_book(book_id):
    book_to_delete = Book.query.get_or_404(book_id)
    if book_to_delete.owner != current_user:
        flash('You do not have permission to delete this book.', 'danger')
        return redirect(url_for('index')), 403 # Forbidden
    
    try:
        db.session.delete(book_to_delete)
        db.session.commit()
        flash(f'Book "{book_to_delete.title}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting book: {str(e)}', 'danger')
        
    return redirect(url_for('index'))
@app.route('/add_book_from_selection', methods=['POST'])
@login_required
def add_book_from_selection():
    book = Book(
        title=request.form['title'],
        authors=request.form['authors'],
        isbn=request.form['isbn'],
        page_count=request.form.get('page_count'),
        average_rating=request.form.get('average_rating'),
        thumbnail_url=request.form['thumbnail_url'],
        user_id=current_user.id
    )
    db.session.add(book)
    db.session.commit()
    flash("Book added successfully!")
    return redirect(url_for('dashboard'))

# Command to create DB and a demo user
# You'll run these commands in the Flask shell:
# flask shell
# > from app import db, User  # or from models import db, User
# > db.create_all()
# > demo_user = User(username='testuser')
# > demo_user.set_password('password123')
# > db.session.add(demo_user)
# > db.session.commit()
# > exit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Creates database tables if they don't exist
        # Optional: Create a default user if one doesn't exist
        if not User.query.filter_by(username='testuser').first():
            print("Creating default user 'testuser' with password 'password123'")
            default_user = User(username='testuser')
            default_user.set_password('password123')
            db.session.add(default_user)
            db.session.commit()
    app.run(debug=True)
