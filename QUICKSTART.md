# CivicAI Quick Start

## 🚀 Start the server (3 simple ways)

### Option 1: One-command startup (Recommended)
```bash
./start.sh
```

### Option 2: Using main.py
```bash
source .venv/bin/activate
python main.py
```

### Option 3: Using uvicorn directly
```bash
source .venv/bin/activate
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

## ✅ What's working

- ✅ **Web Interface**: http://localhost:8000
- ✅ **Health Check**: http://localhost:8000/health
- ✅ **Chat API**: POST http://localhost:8000/chat
- ✅ **Hot Reloading**: Server restarts automatically when you save changes
- ✅ **Demo Mode**: Chat works with demo responses

## 🎯 Features

- **Modern UI**: Beautiful chat interface with dark/light theme
- **Real-time Chat**: Stream responses token by token
- **API Endpoints**: RESTful API for integration
- **Vector Search**: Ready for document search (currently disabled for demo)
- **Hot Reload**: Development-friendly with automatic restarts

## 🔧 Development

The server runs in demo mode by default. To enable real AI responses:

1. Set your OpenAI API key: `export OPENAI_API_KEY="your-key-here"`
2. The chat engine will automatically use real AI responses

## 📁 Project Structure

```
CivicAI/
├── api/           # FastAPI backend
├── web/           # Frontend HTML/CSS/JS
├── data/          # Document data and ingestion
├── main.py        # Entry point
├── start.sh       # Quick start script
└── requirements.txt
```

## 🛠️ Troubleshooting

- **Port 8000 in use**: The start script automatically kills existing processes
- **Import errors**: Make sure virtual environment is activated
- **Dependencies**: Run `pip install -r requirements.txt` if needed

---

**Ready to use!** Open http://localhost:8000 in your browser to start chatting. 