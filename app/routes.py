from flask import render_template, flash, redirect, url_for, abort
from flask_login import login_required
from flask_login import current_user, login_user
from flask_login import logout_user
from flask import request
from urllib.parse import urlsplit
import sqlalchemy as sa
from app import db
from app.models import User, BookSearch
from app import app
from app.forms import RegistrationForm, LoginForm
from datetime import datetime, timezone
from app.forms import EditProfileForm, ClearHistoryForm
import os
import uuid
from werkzeug.utils import secure_filename
from app.isbn import extract_barcode, fetch_book_info

@app.route('/')
@app.route('/index')
def index():
   
    
    return render_template('index.html', title='Home Page')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('You are already logged in. Proceed to your profile.', 'info')
        return redirect(url_for('user', username=current_user.username))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)

        return redirect(url_for('user', username=current_user.username))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)

@app.route('/user/<username>', methods=['GET','POST'])
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))

    book_info = None
    if request.method == 'POST':
        file = request.files['image']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.referrer)
        if file:
            # Secure and uniquely name the file
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)

            isbn = extract_barcode(filepath)
            if isbn:
                book_info = fetch_book_info(isbn)
                if 'error' not in book_info:
                # Save the search to the database
                    new_search = BookSearch(
                        isbn=isbn,
                        title=book_info.get('title'),
                        authors=', '.join(book_info.get('authors', [])),
                        thumbnail=book_info.get('thumbnail'),
                        description=book_info.get('description'),
                        published_date=book_info.get('publishedDate'),
                        user=current_user
                    )
                    db.session.add(new_search)
                    db.session.commit()
            else:
                book_info = {"error": "No valid ISBN found in image"}

            # Optionally: delete the uploaded file after processing
            os.remove(filepath)
    recent_searches = user.book_searches.order_by(BookSearch.timestamp.desc()).limit(10).all()
    clear_form = ClearHistoryForm()
    return render_template('user.html', user=user,  book=book_info, recent_searches=recent_searches,clear_form=clear_form )

@app.route('/clear_history', methods=['POST'])
@login_required
def clear_history():
    form = ClearHistoryForm()
    if form.validate_on_submit():
        BookSearch.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        flash('Your search history has been cleared.', 'success')
    return redirect(url_for('user', username=current_user.username))