# Personal Finance Manager

A Python-based personal finance management application with Telegram bot integration and AI-powered insights.

## Overview

Personal Finance Manager is a modern application that helps users track and manage their personal finances through an intuitive Telegram bot interface and a web dashboard. It leverages AI to provide intelligent spending analysis and financial insights.

## Features

- 📱 **Telegram Bot Integration** - Log expenses and manage finances directly through Telegram
- 💾 **Cloud Database** - Secure data storage with Supabase (PostgreSQL)
- 🤖 **AI-Powered Insights** - Intelligent financial analysis using Groq LLM
- 🌐 **Web Dashboard** - Beautiful frontend deployed on Vercel
- ⚡ **Serverless API** - Fast and scalable REST API built with FastAPI
- 📅 **Smart Date Parsing** - Flexible date input for transaction logging

## Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **Uvicorn** - ASGI web server
- **Pydantic** - Data validation and settings management

### Database & Services
- **Supabase** - PostgreSQL database and backend services
- **Groq** - LLM integration for AI insights

### Bot & Client
- **python-telegram-bot** - Telegram Bot API wrapper
- **httpx** - Modern HTTP client for API requests

### Frontend
- **Vercel** - Deployment platform

## Installation

### Prerequisites
- Python 3.8+
- pip or conda
- Telegram Bot Token (from BotFather)
- Supabase account and API credentials
- Groq API key

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/aniketpawar45/personalfinanacemanager.git
   cd personalfinanacemanager
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   GROQ_API_KEY=your_groq_api_key
   ```

5. **Run the application**
   ```bash
   uvicorn api.main:app --reload
   ```

## Project Structure

```
personalfinanacemanager/
├── api/                    # FastAPI application
│   ├── __init__.py
│   ├── main.py            # Application entry point
│   └── webhook.py         # Telegram webhook handler
├── core/                   # Core business logic
│   ├── __init__.py
│   ├── finance.py         # Finance operations
│   └── utils.py           # Utility functions
├── supabase/              # Database configuration
│   └── migrations/        # Database migrations
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel configuration
└── README.md             # This file
```

## Usage

### Via Telegram Bot

Start the bot with `/start` and use these commands:
- `/add_expense` - Log a new expense
- `/view_expenses` - View recent expenses
- `/summary` - Get spending summary
- `/insights` - Get AI-powered financial insights
- `/help` - Show available commands

### Via API

Example API request:
```bash
curl -X POST http://localhost:8000/api/expenses \
  -H "Content-Type: application/json" \
  -d '{"amount": 50, "category": "food", "date": "2024-01-15"}'
```

## Deployment

### Deploy to Vercel

1. Push your code to GitHub
2. Connect your GitHub repository to Vercel
3. Set environment variables in Vercel dashboard
4. Deploy with one click

The application is already configured with `vercel.json` for webhook routing.

## API Endpoints

- `POST /api/expenses` - Create a new expense
- `GET /api/expenses` - Retrieve expenses
- `GET /api/summary` - Get financial summary
- `POST /api/insights` - Get AI insights
- `POST /api/webhook` - Telegram webhook endpoint

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram Bot API token |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase API key |
| `GROQ_API_KEY` | Groq API key for AI features |

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
This project follows PEP 8 standards. Format code with:
```bash
black .
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is open source and available under the MIT License.

## Support

For support, open an issue on the GitHub repository or contact the maintainer.

## Live Demo

🚀 **Try it out**: [Personal Finance Manager](https://personalfinanacemanager.vercel.app)

---

**Built with ❤️ by [aniketpawar45](https://github.com/aniketpawar45)**
