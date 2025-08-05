
#!/usr/bin/env python3
"""
Simple client startup script
"""

if __name__ == "__main__":
    try:
        from client_app import main
        main()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install PyQt5 psutil")
    except Exception as e:
        print(f"Error starting client: {e}")
        input("Press Enter to exit...")
