#!/usr/bin/env python
"""
Emergency Response Platform - Startup Script

Simplifies launching the entire backend system with proper checks.
Usage: python startup.py
"""

import subprocess
import sys
import os
import time
from pathlib import Path

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def banner():
    print(f"""
{BLUE}{BOLD}
======================================================================
  EMERGENCY RESPONSE COORDINATION PLATFORM - STARTUP
  Version 1.0 (HTTP Polling - No WebSocket)
======================================================================
{RESET}
    """)

def check_python_version():
    """Verify Python version >= 3.8"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"{RED}❌ Python 3.8+ required. Current: {version.major}.{version.minor}{RESET}")
        return False
    print(f"{GREEN}✅ Python version: {version.major}.{version.minor}{RESET}")
    return True

def check_dependencies():
    """Verify required packages are installed"""
    required = ['fastapi', 'sqlalchemy']
    missing = []
    
    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print(f"{GREEN}✅ {package}{RESET}")
        except ImportError:
            missing.append(package)
            print(f"{RED}❌ {package}{RESET}")
    
    if missing:
        print(f"\n{YELLOW}⚠️  Missing packages. Installing...{RESET}")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '-q'])
        return True
    return True

def check_files():
    """Verify required files exist"""
    required_files = [
        'api/unified_api.py',
        'api/websocket_manager.py',
        'api/incident_service.py',
        'api/vehicle_simulator.py',
        'models/db_schema.py',
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"{GREEN}✅ {file_path}{RESET}")
        else:
            print(f"{RED}❌ {file_path} NOT FOUND{RESET}")
            all_exist = False
    
    return all_exist

def display_config():
    """Display configuration"""
    print(f"\n{BOLD}Configuration:{RESET}")
    print(f"  API Host: {BLUE}localhost{RESET}")
    print(f"  API Port: {BLUE}8000{RESET}")
    print(f"  Swagger UI: {BLUE}http://localhost:8000/docs{RESET}")
    print(f"  WebSocket Base: {BLUE}ws://localhost:8000{RESET}")
    print(f"  Database: SQLite (in-memory) or PostgreSQL if configured")

def start_api():
    """Start the FastAPI server"""
    print(f"\n{BOLD}Starting API Server...{RESET}")
    
    os.chdir('api')
    
    try:
        # Try with uvicorn
        cmd = [
            sys.executable, '-m', 'uvicorn',
            'unified_api:app',
            '--reload',
            '--host', '0.0.0.0',
            '--port', '8000'
        ]
        
        print(f"{YELLOW}Running: {' '.join(cmd)}{RESET}\n")
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print(f"\n{YELLOW}⚠️  API Server stopped by user{RESET}")
    except Exception as e:
        print(f"{RED}❌ Error starting API: {e}{RESET}")
        return False
    
    return True

def main():
    banner()
    
    print(f"{BOLD}Pre-startup Checks:{RESET}\n")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check dependencies
    print(f"\n{BOLD}Checking dependencies:{RESET}")
    check_dependencies()
    
    # Check files
    print(f"\n{BOLD}Checking required files:{RESET}")
    if not check_files():
        print(f"{RED}❌ Some required files are missing!{RESET}")
        sys.exit(1)
    
    # Display config
    display_config()
    
    # Start API
    print(f"\n{YELLOW}{'='*76}{RESET}")
    print(f"{BOLD}Starting Emergency Response Platform...{RESET}")
    print(f"{YELLOW}{'='*76}{RESET}\n")
    
    start_api()

if __name__ == '__main__':
    main()
