from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure
from bson import ObjectId
from dotenv import load_dotenv
import os
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')  # Required for flash messages

# Configure logging
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('People Management System startup')

def get_db():
    """Get MongoDB database connection."""
    try:
        client = MongoClient(os.getenv("MONGO_URI"))
        db = client.test_database
        collection = db.personas
        # Create indexes for better performance
        collection.create_index([("name", ASCENDING)])
        collection.create_index([("city", ASCENDING)])
        return collection
    except ConnectionFailure as e:
        app.logger.error(f"Error connecting to MongoDB Atlas: {e}")
        raise

def get_pagination(page, per_page=10):
    """Calculate pagination values."""
    return {
        'skip': (page - 1) * per_page,
        'limit': per_page
    }

@app.route('/')
def show_people():
    """Show all people with pagination, search, and sorting."""
    try:
        collection = get_db()
        # Get query parameters
        page = int(request.args.get('page', 1))
        search = request.args.get('search', '')
        sort_by = request.args.get('sort_by', 'name')  # Default to 'name' if empty
        order = request.args.get('order', 'asc')
        
        # Build query
        query = {}
        if search:
            query = {
                '$or': [
                    {'name': {'$regex': search, '$options': 'i'}},
                    {'city': {'$regex': search, '$options': 'i'}}
                ]
            }
        
        # Get total count for pagination
        total = collection.count_documents(query)
        per_page = 10
        total_pages = (total + per_page - 1) // per_page
        
        # Ensure page is within valid range
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1
        
        # Get pagination values
        pagination = get_pagination(page, per_page)
        
        # Build sort - ensure sort_by is not empty
        if not sort_by:
            sort_by = 'name'  # Default to 'name' if empty
        sort_direction = ASCENDING if order == 'asc' else DESCENDING
        sort = [(sort_by, sort_direction)]
        
        # Get people with pagination and sorting
        people = collection.find(query).sort(sort).skip(pagination['skip']).limit(pagination['limit'])
        
        return render_template('index.html',
                             people=people,
                             current_page=page,
                             total_pages=total_pages,
                             search=search,
                             sort_by=sort_by,
                             order=order)
    except Exception as e:
        app.logger.error(f"Error in show_people: {e}")
        return render_template('500.html', error="Database connection error. Please try again later."), 500

@app.route('/add', methods=['GET', 'POST'])
def add_person():
    """Add a new person to the collection."""
    if request.method == 'POST':
        try:
            collection = get_db()
            # Validate input
            name = request.form.get('name', '').strip()
            age = request.form.get('age', '').strip()
            city = request.form.get('city', '').strip()
            
            if not all([name, age, city]):
                flash('All fields are required.', 'danger')
                return render_template('add.html')
            
            try:
                age = int(age)
                if age < 0 or age > 150:
                    raise ValueError
            except ValueError:
                flash('Age must be a valid number between 0 and 150.', 'danger')
                return render_template('add.html')
            
            new_person = {
                'name': name,
                'age': age,
                'city': city,
                'created_at': datetime.utcnow()
            }
            
            result = collection.insert_one(new_person)
            if result.inserted_id:
                flash('Person added successfully!', 'success')
                return redirect(url_for('show_people'))
            else:
                flash('Failed to add person.', 'danger')
                return render_template('add.html')
                
        except Exception as e:
            app.logger.error(f"Error in add_person: {e}")
            flash('An error occurred while adding the person.', 'danger')
            return render_template('add.html')
            
    return render_template('add.html')

@app.route('/edit/<person_id>', methods=['GET', 'POST'])
def edit_person(person_id):
    """Edit a person's information."""
    try:
        collection = get_db()
        person = collection.find_one({'_id': ObjectId(person_id)})
        if not person:
            flash('Person not found.', 'danger')
            return redirect(url_for('show_people'))
        
        if request.method == 'POST':
            try:
                # Validate input
                name = request.form.get('name', '').strip()
                age = request.form.get('age', '').strip()
                city = request.form.get('city', '').strip()
                
                if not all([name, age, city]):
                    flash('All fields are required.', 'danger')
                    return render_template('edit.html', person=person)
                
                try:
                    age = int(age)
                    if age < 0 or age > 150:
                        raise ValueError
                except ValueError:
                    flash('Age must be a valid number between 0 and 150.', 'danger')
                    return render_template('edit.html', person=person)
                
                updated_person = {
                    'name': name,
                    'age': age,
                    'city': city,
                    'updated_at': datetime.utcnow()
                }
                
                result = collection.update_one(
                    {'_id': ObjectId(person_id)},
                    {'$set': updated_person}
                )
                
                if result.modified_count > 0:
                    flash('Person updated successfully!', 'success')
                    return redirect(url_for('show_people'))
                else:
                    flash('No changes were made.', 'info')
                    return render_template('edit.html', person=person)
                    
            except Exception as e:
                app.logger.error(f"Error in edit_person POST: {e}")
                flash('An error occurred while updating the person.', 'danger')
                return render_template('edit.html', person=person)
                
        return render_template('edit.html', person=person)
        
    except Exception as e:
        app.logger.error(f"Error in edit_person: {e}")
        flash('An error occurred.', 'danger')
        return redirect(url_for('show_people'))

@app.route('/delete/<person_id>')
def delete_person(person_id):
    """Delete a person from the collection."""
    try:
        collection = get_db()
        result = collection.delete_one({'_id': ObjectId(person_id)})
        if result.deleted_count > 0:
            flash('Person deleted successfully!', 'success')
        else:
            flash('Person not found.', 'danger')
    except Exception as e:
        app.logger.error(f"Error in delete_person: {e}")
        flash('An error occurred while deleting the person.', 'danger')
    return redirect(url_for('show_people'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
