import hashlib
import logging
import sqlite3
import sys
import re

logger = logging.getLogger("authentication_logger")
handler = logging.FileHandler("/tmp/authentication.log")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

db_path = "/etc/freeradius/3.0/scripts/AKGECWifi/db.sqlite3"

def sanitize_input(username, password):
    # Validate username: Only alphanumeric characters, underscores, and no longer than 50 characters
    if not re.match("^[A-Za-z0-9_]{1,50}$", username):
        logger.warning(f"Invalid username format: {username}")
        return None, None  # Return None to indicate invalid input

    # Sanitize password: Remove non-alphanumeric characters and strip whitespace
    password = re.sub(r'[^A-Za-z0-9!@#$%^&*()_+={}\[\]:;"\'<>,.?/-]', '', password.strip())



    return username, password

def authenticate_user(username, password):
    try:
        hashed_input_password = hashlib.md5(password.encode()).hexdigest()

        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        
        cursor.execute(
            "SELECT password FROM captive_portal_studentmodel WHERE username = ?",
            (username,),
        )

        result = cursor.fetchone()

        if result:
            stored_password = result[0]

            if hashed_input_password == stored_password:
                logger.info(f"Login success for username: {username}")
                print("Auth-Type := Accept")
                return 0  # Return 0 to indicate success
            else:
                logger.warning(f"Login failed for username: {username}")
                print("Auth-Type := Reject")
                return 1  # Return 1 to indicate failure
        else:
            logger.warning(f"Login failed for username: {username} (user not found)")
            print("Auth-Type := Reject")
            return 1  # Return 1 to indicate failure

        connection.close()

    except Exception as e:
        logger.error(f"Error during authentication: {str(e)}")
        print("Auth-Type := Reject")
        return 1  # Return 1 to indicate failure


if __name__ == "__main__":
    # Simulated values for username and password

    username = sys.argv[1]
    password = sys.argv[2]
    username, password = sanitize_input(username, password)


    exit_code = authenticate_user(username, password)
    exit(exit_code)
