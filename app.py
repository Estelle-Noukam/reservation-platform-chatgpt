from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ======================
# MODELS
# ======================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=False)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reservation_date = db.Column(db.String(100), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'))

    user = db.relationship('User', backref='reservations')
    resource = db.relationship('Resource', backref='reservations')

# ======================
# DATABASE INIT
# ======================

with app.app_context():
    db.create_all()

    admin_exists = User.query.filter_by(username='admin').first()

    if not admin_exists:
        admin = User(
            username='admin',
            password=generate_password_hash('admin'),
            role='admin'
        )

        db.session.add(admin)

        default_resources = [
            Resource(name='Salle A', description='Grande salle de réunion'),
            Resource(name='Projecteur', description='Projecteur HD'),
            Resource(name='Service Nettoyage', description='Service professionnel')
        ]

        db.session.add_all(default_resources)

        db.session.commit()

# ======================
# HELPERS
# ======================

def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def is_admin():
    user = current_user()
    return user and user.role == 'admin'

# ======================
# ROUTES
# ======================

@app.route('/')
def index():
    return render_template('index.html', user=current_user())

# ======================
# AUTH
# ======================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash('Utilisateur déjà existant')
            return redirect(url_for('register'))

        new_user = User(
            username=username,
            password=generate_password_hash(password),
            role='user'
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html', user=current_user())

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            session['user_id'] = user.id

            return redirect(url_for('index'))

        flash('Identifiants invalides')

    return render_template('login.html', user=current_user())

@app.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('index'))

# ======================
# PROFILE
# ======================

@app.route('/profile')
def profile():

    user = current_user()

    if not user:
        return redirect(url_for('login'))

    return render_template('profile.html', user=user)

# ======================
# RESOURCES
# ======================

@app.route('/resources')
def resources():

    resources = Resource.query.all()

    return render_template(
        'resources.html',
        resources=resources,
        user=current_user()
    )

# ======================
# BOOK RESOURCE
# ======================

@app.route('/book/<int:resource_id>', methods=['GET', 'POST'])
def book_resource(resource_id):

    user = current_user()

    if not user:
        return redirect(url_for('login'))

    resource = Resource.query.get_or_404(resource_id)

    if request.method == 'POST':

        reservation_date = request.form['reservation_date']

        reservation = Reservation(
            reservation_date=reservation_date,
            user_id=user.id,
            resource_id=resource.id
        )

        db.session.add(reservation)
        db.session.commit()

        return redirect(url_for('reservations'))

    return render_template(
        'book_resource.html',
        resource=resource,
        user=user
    )

# ======================
# USER RESERVATIONS
# ======================

@app.route('/reservations')
def reservations():

    user = current_user()

    if not user:
        return redirect(url_for('login'))

    reservations = Reservation.query.filter_by(user_id=user.id).all()

    return render_template(
        'reservations.html',
        reservations=reservations,
        user=user
    )

# ======================
# CANCEL RESERVATION
# ======================

@app.route('/cancel/<int:reservation_id>')
def cancel_reservation(reservation_id):

    user = current_user()

    if not user:
        return redirect(url_for('login'))

    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.user_id != user.id and not is_admin():
        return redirect(url_for('reservations'))

    db.session.delete(reservation)
    db.session.commit()

    return redirect(url_for('reservations'))

# ======================
# ADMIN RESOURCES
# ======================

@app.route('/admin/resources')
def admin_resources():

    if not is_admin():
        return redirect(url_for('index'))

    resources = Resource.query.all()

    return render_template(
        'admin_resources.html',
        resources=resources,
        user=current_user()
    )

@app.route('/admin/resources/create', methods=['GET', 'POST'])
def create_resource():

    if not is_admin():
        return redirect(url_for('index'))

    if request.method == 'POST':

        name = request.form['name']
        description = request.form['description']

        resource = Resource(
            name=name,
            description=description
        )

        db.session.add(resource)
        db.session.commit()

        return redirect(url_for('admin_resources'))

    return render_template(
        'create_resource.html',
        user=current_user()
    )

@app.route('/admin/resources/edit/<int:id>', methods=['GET', 'POST'])
def edit_resource(id):

    if not is_admin():
        return redirect(url_for('index'))

    resource = Resource.query.get_or_404(id)

    if request.method == 'POST':

        resource.name = request.form['name']
        resource.description = request.form['description']

        db.session.commit()

        return redirect(url_for('admin_resources'))

    return render_template(
        'edit_resource.html',
        resource=resource,
        user=current_user()
    )

@app.route('/admin/resources/delete/<int:id>')
def delete_resource(id):

    if not is_admin():
        return redirect(url_for('index'))

    resource = Resource.query.get_or_404(id)

    db.session.delete(resource)
    db.session.commit()

    return redirect(url_for('admin_resources'))

# ======================
# ADMIN RESERVATIONS
# ======================

@app.route('/admin/reservations')
def admin_reservations():

    if not is_admin():
        return redirect(url_for('index'))

    reservations = Reservation.query.all()

    return render_template(
        'admin_reservations.html',
        reservations=reservations,
        user=current_user()
    )

# ======================
# RUN
# ======================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
