from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm
from forms import RegistrationForm, LoginForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length
import requests
from models import db, User, Book

# App Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database and Login Manager Initialization
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Context processor to inject site name into all templates
@app.context_processor
def inject_site_name():
    return dict(site_name="LandOBooks")

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Routes
@app.route('/')
@login_required
def index():
    user_books = Book.query.filter_by(user_id=current_user.id).order_by(Book.title).all()
    return render_template('index.html', books=user_books)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username already exists.', 'warning')
            return redirect(url_for('register'))

        new_user = User(username=form.username.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        flash('Invalid username or password.', 'danger')

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/search', methods=['POST'])
@login_required
def search():
    query = request.form['query']
    search_type = request.form['search_type']
    url = f'https://www.googleapis.com/books/v1/volumes?q={search_type}:{query}'

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'items' not in data or not data['items']:
            flash("No results found.", "warning")
            return redirect(url_for('index'))
        return render_template('choose_book.html', books=data['items'])

    except requests.exceptions.RequestException as e:
        flash(f"API error: {e}", "danger")
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
    return redirect(url_for('index'))

@app.route('/add_book', methods=['POST'])
@login_required
def add_book():
    isbn = request.form.get('isbn')
    if not isbn:
        flash('ISBN is required.', 'warning')
        return redirect(url_for('index'))

    existing_book = Book.query.filter_by(user_id=current_user.id, isbn=isbn).first()
    if existing_book:
        flash(f'Book with ISBN {isbn} already in your catalogue.', 'info')
        return redirect(url_for('index'))

    return redirect(url_for('search'))

@app.route('/delete_book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    book_to_delete = Book.query.get_or_404(book_id)
    if book_to_delete.owner != current_user:
        flash('You do not have permission to delete this book.', 'danger')
        return redirect(url_for('index')), 403

    try:
        db.session.delete(book_to_delete)
        db.session.commit()
        flash(f'Book "{book_to_delete.title}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting book: {str(e)}', 'danger')

    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)


