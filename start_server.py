
#!/usr/bin/env python3
"""
Simple server startup script
"""

if __name__ == "__main__":
    try:
        from server_app import main
        main()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install PyQt5 psutil")
    except Exception as e:
        print(f"Error starting server: {e}")
        input("Press Enter to exit...")
