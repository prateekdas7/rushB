from flask import Flask
import os

def get_database_credentials():
    print("\n" + "="*50)
    print("RushB - CS:GO Tournament Management System")
    print("="*50)
    print("\nDatabase Connection Required")
    print("-"*50)
    db_host = input("Enter MySQL Host (default: localhost): ").strip() or "localhost"
    db_port = input("Enter MySQL Port (default: 3306): ").strip() or "3306"
    db_name = input("Enter Database Name (default: rushb): ").strip() or "rushb"
    db_user = input("Enter MySQL Username: ").strip()
    if not db_user:
        print("Error: Username cannot be empty!")
        return get_database_credentials()
    db_password = input("Enter MySQL Password: ").strip()
    print("-"*50 + "\n")

    return {
        'host': db_host,
        'port': db_port,
        'name': db_name,
        'user': db_user,
        'password': db_password
    }

#Creates the App accordingly.
def create_app():
    from config import Config
    from routes import init_routes

    app = Flask(__name__)
    #Sets the flask config from config.py
    app.config.from_object(Config)

    # Initialize routes
    init_routes(app)

    return app

#This app runs when executed as a command on CLI. So __name__ == __main__.
if __name__ == '__main__':
    # Get database credentials from user.
    credentials = get_database_credentials()

    # Set environment variables.
    os.environ['DB_HOST'] = credentials['host']
    os.environ['DB_PORT'] = credentials['port']
    os.environ['DB_NAME'] = credentials['name']
    os.environ['DB_USER'] = credentials['user']
    os.environ['DB_PASSWORD'] = credentials['password']

    #Import DB
    from database.db import test_connection

    # Test database connection with provided credentials
    print("Testing database connection...")
    if test_connection():
        print("Database connection successful!")

        # Create and run the app
        app = create_app()
        print("\n" + "="*50)
        print("Server starting...")
        print(f"Access the application at: http://localhost:5000")
        print("="*50 + "\n")

        # Set the config for running the app.py
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    else:
        print("\nFailed to connect to database.")
        print("Please check your credentials and try again.")
        print("\nConnection details used:")
        print(f"  Host: {credentials['host']}")
        print(f"  Port: {credentials['port']}")
        print(f"  Database: {credentials['name']}")
        print(f"  User: {credentials['user']}")
        print("\nMake sure:")
        print("  1. MySQL server is running")
        print("  2. Database exists")
        print("  3. Username and password are correct")
        print("  4. User has proper permissions")