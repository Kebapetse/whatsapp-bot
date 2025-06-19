# WhatsApp Business Directory Bot

A WhatsApp bot that allows users to search for local businesses and register their own businesses in a directory. Built with Flask, Twilio, and Firebase Firestore.

## Features

### For Customers:
- 🔍 **Search Businesses**: Send keywords like "pizza", "hotel", "pharmacy" to find relevant businesses
- 📱 **Easy Interface**: Simple text-based commands via WhatsApp
- 📍 **Local Results**: Find businesses with contact details and addresses

### For Business Owners:
- 📝 **Free Registration**: Add your business to the directory in 5 simple steps
- 🏷️ **Keyword Tagging**: Tag your business with relevant keywords for better discovery
- 📞 **Contact Information**: Include phone, email, and address for customer contact
- ✅ **Instant Listing**: Business appears in search results immediately after registration

## Bot Commands

- **Search**: Send any keyword (e.g., "restaurant", "hotel", "pharmacy")
- **Register**: Send "register" to add your business
- **Help**: Send "help", "start", or "menu" for command list
- **Contact**: Send "contact" for support information
- **Cancel**: Send "cancel" during registration to stop the process

## Technical Stack

- **Backend**: Flask (Python)
- **Messaging**: Twilio WhatsApp API
- **Database**: Firebase Firestore
- **Deployment**: Render.com
- **Environment**: Python 3.9+

## Setup Instructions

### Prerequisites
- Python 3.9+
- Twilio Account with WhatsApp API access
- Firebase Project with Firestore enabled
- Render.com account (for deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd whatsapp-business-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

4. **Set up Firebase**
   - Create a Firebase project
   - Enable Firestore database
   - Generate a service account key (JSON)
   - Copy the entire JSON content as a single line to `FIREBASE_JSON` in your `.env`

5. **Set up Twilio**
   - Get WhatsApp API access from Twilio
   - Add your Account SID and Auth Token to `.env`
   - Configure webhook URL in Twilio Console

6. **Run locally**
   ```bash
   python app.py
   ```

### Deployment to Render

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Create Render Web Service**
   - Connect your GitHub repository
   - Use the provided `render.yaml` configuration
   - Set environment variables in Render dashboard:
     - `FIREBASE_JSON`: Your Firebase service account JSON (as single line)
     - `TWILIO_ACCOUNT_SID`: Your Twilio Account SID
     - `TWILIO_AUTH_TOKEN`: Your Twilio Auth Token

3. **Configure Twilio Webhook**
   - Set webhook URL to: `https://your-render-app.onrender.com/webhook`
   - Method: POST

## Database Schema

### Businesses Collection
```javascript
{
  "name": "Mario's Pizza Restaurant",
  "name_lower": "mario's pizza restaurant",
  "address": "123 Main Street, Downtown, City",
  "phone": "+1234567890",
  "email": "info@mariospizza.com",
  "keywords": ["pizza", "restaurant", "italian", "delivery"],
  "registered_by": "whatsapp:+1234567890",
  "registered_at": "2024-01-15T10:30:00Z",
  "status": "active"
}
```

## Usage Examples

### Searching for Businesses
```
User: pizza
Bot: 🔍 Found 3 business(es) for 'pizza':

1. *Mario's Pizza Restaurant*
📍 123 Main Street, Downtown, City
📞 +1234567890
📧 info@mariospizza.com

2. *Tony's Italian Kitchen*
📍 456 Oak Ave, Uptown, City
📞 +1234567891

...
```

### Registering a Business
```
User: register
Bot: 📝 Business Registration

Let's add your business to our directory!

Step 1 of 5: What's your business name?

User: Mario's Pizza
Bot: ✅ Business name: Mario's Pizza

Step 2 of 5: What's your business address?
...
```

## Error Handling

The bot includes comprehensive error handling for:
- Database connection issues
- Invalid input validation
- Network timeouts
- Registration process interruptions
- Search query errors

## Security Features

- Environment variables for sensitive data
- Input validation and sanitization
- Phone number and email format validation
- Session management for registration process
- Error logging without exposing sensitive information

## Monitoring and Logs

- Health check endpoint: `GET /`
- Comprehensive logging for debugging
- Error tracking and reporting
- Request/response monitoring

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## Support

For support or questions:
- Email: support@yourdomain.com
- Create an issue in this repository

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Made with ❤️ for local businesses**