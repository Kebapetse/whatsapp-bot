import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
import logging

logger = logging.getLogger(__name__)

def init_firestore():
    """Initialize and return Firestore database client"""
    try:
        # Check if Firebase app is already initialized
        try:
            app = firebase_admin.get_app()
            logger.info("Firebase app already initialized")
        except ValueError:
            # App not initialized, so initialize it
            firebase_json = os.getenv('FIREBASE_JSON')
            
            if not firebase_json:
                raise ValueError("FIREBASE_JSON environment variable not set")
            
            # Parse the JSON string
            try:
                service_account_info = json.loads(firebase_json)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in FIREBASE_JSON: {e}")
            
            # Initialize Firebase Admin SDK
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase app initialized successfully")
        
        # Return Firestore client
        db = firestore.client()
        logger.info("Firestore client created successfully")
        return db
        
    except Exception as e:
        logger.error(f"Failed to initialize Firebase/Firestore: {e}")
        raise e