from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from database_config import get_db
import logging
import os
import re
from datetime import datetime

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database manager
db = get_db()

# Store user registration sessions in memory
user_sessions = {}

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint for Render"""
    try:
        business_count = db.get_business_count()
        return {
            "status": "healthy", 
            "service": "whatsapp-bot",
            "businesses_count": business_count,
            "database": "sqlite"
        }, 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}, 500

def validate_phone(phone):
    """Validate phone number format"""
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    # Check if it looks like a valid phone number
    return len(cleaned) >= 10 and (cleaned.startswith('+') or cleaned.isdigit())

def validate_email(email):
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    """Main webhook endpoint for WhatsApp messages"""
    try:
        # Get message details
        body = request.form.get('Body', '').strip()
        from_number = request.form.get('From', '')
        
        logger.info(f"Received message: '{body}' from {from_number}")
        
        resp = MessagingResponse()

        # Handle empty message
        if not body:
            resp.message("👋 Welcome to Business Directory!\n\n🔍 *Search*: Send keywords like 'pizza', 'hotel'\n📝 *Register*: Send 'register' to add your business\n❓ *Help*: Send 'help' for more options")
            return str(resp)

        body_lower = body.lower()

        # Check if user is in a registration session
        if from_number in user_sessions:
            return handle_registration_step(from_number, body, resp)

        # Handle commands
        if body_lower in ['help', 'start', 'menu']:
            help_message = """🏢 *Business Directory Bot*

🔍 *SEARCH FOR BUSINESSES:*
Send keywords like:
• restaurant, pizza, food
• hotel, accommodation  
• pharmacy, medicine
• repair, tech, service

📍 *SEARCH BY LOCATION:*
• "near downtown" - Find businesses near downtown
• "near airport" - Find businesses near airport

📝 *REGISTER YOUR BUSINESS:*
• Send 'register' to add your business
• It's FREE and takes 2 minutes!

❓ *OTHER COMMANDS:*
• 'help' - Show this menu
• 'contact' - Get support
• 'stats' - Directory statistics"""
            resp.message(help_message)
            return str(resp)

        elif body_lower == 'register':
            return start_registration(from_number, resp)

        elif body_lower == 'contact':
            resp.message("📞 *Need Help?*\n\nFor support or questions:\n• Email: support@yourdomain.com\n• Reply 'help' for commands")
            return str(resp)
        
        elif body_lower == 'stats':
            return show_statistics(resp)
        
        elif body_lower.startswith('near '):
            location = body_lower[5:].strip()  # Remove 'near ' prefix
            return search_by_location(location, resp)

        # Default: Search for businesses
        else:
            return search_businesses(body_lower, resp)

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        resp = MessagingResponse()
        resp.message("Sorry, something went wrong. Please try again or send 'help' for assistance.")
        return str(resp)

def show_statistics(resp):
    """Show directory statistics"""
    try:
        total_count = db.get_business_count()
        recent_businesses = db.get_recent_businesses(3)
        popular_keywords = db.get_popular_keywords(5)
        
        stats_message = f"📊 *Directory Statistics*\n\n"
        stats_message += f"🏢 Total Businesses: {total_count}\n\n"
        
        if recent_businesses:
            stats_message += "🆕 *Recently Added:*\n"
            for business in recent_businesses:
                # Format the datetime
                reg_date = business['registered_at']
                if isinstance(reg_date, str):
                    reg_date = datetime.fromisoformat(reg_date.replace('Z', '+00:00'))
                formatted_date = reg_date.strftime('%b %d')
                stats_message += f"• {business['name']} ({formatted_date})\n"
        
        if popular_keywords:
            stats_message += f"\n🔥 *Popular Categories:*\n"
            for kw in popular_keywords:
                stats_message += f"• {kw['keyword']} ({kw['count']})\n"
        
        stats_message += f"\n💡 Send 'register' to add your business FREE!"
        
        resp.message(stats_message)
        return str(resp)
        
    except Exception as e:
        logger.error(f"Error showing statistics: {e}")
        resp.message("📊 Directory is growing daily!\n\n💡 Send 'register' to add your business FREE!")
        return str(resp)

def search_by_location(location, resp):
    """Search for businesses by location"""
    try:
        results = db.search_by_location(location, limit=10)
        
        if results:
            reply = f"📍 Found {len(results)} business(es) near '{location}':\n\n"
            for i, business in enumerate(results[:5], 1):
                name = business.get('name', 'Unknown Business')
                address = business.get('address', 'Address not available')
                phone = business.get('phone', 'Phone not available')
                keywords = business.get('keywords', [])
                
                reply += f"{i}. *{name}*\n"
                reply += f"📍 {address}\n"
                reply += f"📞 {phone}\n"
                if keywords:
                    reply += f"🏷️ {', '.join(keywords[:3])}\n"
                reply += "\n"
            
            if len(results) > 5:
                reply += f"... and {len(results) - 5} more results.\n\n"
                
            reply += "💡 Try searching by business type too!"
        else:
            reply = f"""📍 No businesses found near '{location}'.

💡 *Try searching by:*
• Business type: restaurant, hotel, pharmacy
• Different location: downtown, airport, mall
• Send 'register' to add your business"""

        resp.message(reply)
        return str(resp)

    except Exception as e:
        logger.error(f"Location search error: {e}")
        resp.message("Sorry, there was an error searching by location. Please try again.")
        return str(resp)

def start_registration(from_number, resp):
    """Start business registration process"""
    user_sessions[from_number] = {
        'step': 'name',
        'data': {}
    }
    
    resp.message("""📝 *Business Registration*

Let's add your business to our directory!

*Step 1 of 5:* What's your business name?

Example: "Mario's Pizza Restaurant"

💡 Type 'cancel' anytime to stop registration.""")
    
    return str(resp)

def handle_registration_step(from_number, body, resp):
    """Handle each step of the registration process"""
    session = user_sessions[from_number]
    step = session['step']
    
    # Check if user wants to cancel
    if body.lower() == 'cancel':
        del user_sessions[from_number]
        resp.message("❌ Registration cancelled. Send 'register' to start again or 'help' for other options.")
        return str(resp)
    
    if step == 'name':
        if len(body.strip()) < 2:
            resp.message("⚠️ Business name seems too short. Please enter your full business name:")
            return str(resp)
        
        session['data']['name'] = body.strip()
        session['step'] = 'address'
        resp.message(f"""✅ Business name: {body.strip()}

*Step 2 of 5:* What's your business address?

Example: "123 Main Street, Downtown, City"

Include area/neighborhood for better visibility!""")
    
    elif step == 'address':
        if len(body.strip()) < 10:
            resp.message("⚠️ Please provide a more complete address including street and area:")
            return str(resp)
        
        session['data']['address'] = body.strip()
        session['step'] = 'phone'
        resp.message(f"""✅ Address saved!

*Step 3 of 5:* What's your business phone number?

Example: "+1234567890" or "0712345678"

This helps customers contact you directly.""")
    
    elif step == 'phone':
        if not validate_phone(body):
            resp.message("⚠️ Please enter a valid phone number:\n\nExamples:\n• +1234567890\n• 0712345678\n• 555-123-4567")
            return str(resp)
        
        session['data']['phone'] = body.strip()
        session['step'] = 'email'
        resp.message(f"""✅ Phone number saved!

*Step 4 of 5:* What's your business email? (Optional)

Example: "info@mybusiness.com"

💡 Send 'skip' if you don't have a business email.""")
    
    elif step == 'email':
        if body.lower() == 'skip':
            session['data']['email'] = 'Not provided'
        elif validate_email(body):
            session['data']['email'] = body.strip()
        else:
            resp.message("⚠️ Please enter a valid email address or send 'skip':\n\nExample: info@mybusiness.com")
            return str(resp)
        
        session['step'] = 'keywords'
        resp.message(f"""✅ Email saved!

*Step 5 of 5:* What keywords describe your business?

Separate with commas. This helps customers find you!

Examples:
• "pizza, restaurant, italian, delivery"
• "hotel, accommodation, lodging"
• "pharmacy, medicine, health, drugs"

💡 Include 3-8 relevant keywords.""")
    
    elif step == 'keywords':
        keywords_raw = [k.strip().lower() for k in body.split(',')]
        keywords = [k for k in keywords_raw if len(k) > 1]  # Filter out very short keywords
        
        if len(keywords) < 2:
            resp.message("⚠️ Please provide at least 2 keywords, separated by commas:\n\nExample: restaurant, pizza, delivery, italian")
            return str(resp)
        
        session['data']['keywords'] = keywords
        return complete_registration(from_number, resp)
    
    return str(resp)

def complete_registration(from_number, resp):
    """Complete the business registration"""
    try:
        session = user_sessions[from_number]
        business_data = session['data']
        
        # Prepare data for database
        business_doc = {
            'name': business_data['name'],
            'address': business_data['address'],
            'phone': business_data['phone'],
            'email': business_data['email'],
            'keywords': business_data['keywords'],
            'registered_by': from_number
        }
        
        # Add to database
        business_id = db.add_business(business_doc)
        
        # Clean up session
        del user_sessions[from_number]
        
        # Send confirmation
        confirmation = f"""🎉 *Registration Complete!*

Your business has been added to our directory:

🏢 *{business_data['name']}*
📍 {business_data['address']}
📞 {business_data['phone']}
📧 {business_data['email']}
🏷️ Keywords: {', '.join(business_data['keywords'])}

✅ Customers can now find your business by searching for any of your keywords!

💡 *Tips:*
• Share this bot with customers
• Tell them to search: {business_data['keywords'][0]}
• Need changes? Contact support

Thank you for joining our directory! 🙏

Business ID: #{business_id}"""
        
        resp.message(confirmation)
        
        logger.info(f"New business registered: {business_data['name']} (ID: {business_id}) by {from_number}")
        
    except Exception as e:
        logger.error(f"Registration completion error: {e}")
        # Clean up session anyway
        if from_number in user_sessions:
            del user_sessions[from_number]
        resp.message("❌ Sorry, there was an error completing your registration. Please try again later or contact support.")
    
    return str(resp)

def search_businesses(query, resp):
    """Search for businesses based on query"""
    try:
        results = db.search_businesses(query, limit=10)
        
        if results:
            reply = f"🔍 Found {len(results)} business(es) for '{query}':\n\n"
            for i, business in enumerate(results[:5], 1):  # Limit to 5 results for WhatsApp
                name = business.get('name', 'Unknown Business')
                address = business.get('address', 'Address not available')
                phone = business.get('phone', 'Phone not available')
                email = business.get('email', 'Not provided')
                
                reply += f"{i}. *{name}*\n"
                reply += f"📍 {address}\n"
                reply += f"📞 {phone}\n"
                if email != 'Not provided':
                    reply += f"📧 {email}\n"
                reply += "\n"
            
            if len(results) > 5:
                reply += f"... and {len(results) - 5} more results.\n\n"
            
            reply += "💡 Can't find what you're looking for?\n• Try different keywords\n• Send 'register' to add your business"
        else:
            reply = f"""❌ No businesses found for '{query}'.

💡 *Try these keywords:*
• restaurant, pizza, food
• hotel, accommodation
• pharmacy, medicine
• repair, service

🏢 *Own a business?*
Send 'register' to add it FREE!"""

        resp.message(reply)
        return str(resp)

    except Exception as e:
        logger.error(f"Search error: {e}")
        resp.message("Sorry, there was an error searching. Please try again.")
        return str(resp)

@app.errorhandler(404)
def not_found(error):
    return {"error": "Endpoint not found"}, 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return {"error": "Internal server error"}, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)