"""Entry point for running the FastAPI server."""

import sys
import uvicorn

def main():
    try:
        # Import the app to ensure it's available
        from api.app import app
        print("✅ App imported successfully")
        
        # Start the server
        print("🚀 Starting CivicAI server on http://localhost:8000")
        uvicorn.run(
            "api.app:app", 
            host="0.0.0.0", 
            port=8000, 
            reload=True,
            log_level="info"
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
