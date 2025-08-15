#!/usr/bin/env python
"""Test script to verify all components work."""

import asyncio
import sys
from pathlib import Path

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        # Test domain models
        from src.domain.models.submission import Submission
        from src.domain.models.sample import Sample
        print("✅ Domain models imported")
        
        # Test infrastructure
        from src.infrastructure.config.settings import Settings
        from src.infrastructure.persistence.database import Database
        print("✅ Infrastructure imported")
        
        # Test application
        from src.application.container import Container
        print("✅ Application imported")
        
        # Test presentation
        from src.presentation.api.app import app
        print("✅ API imported")
        
        # Test web UI
        from src.presentation.web.server import app as web_app
        print("✅ Web UI imported")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_configuration():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from src.infrastructure.config.settings import get_settings
        settings = get_settings()
        
        print(f"✅ Environment: {settings.environment}")
        print(f"✅ API Port: {settings.port}")
        print(f"✅ Web Port: {settings.web_port}")
        print(f"✅ Database: {settings.database_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False

def test_database():
    """Test database connection."""
    print("\nTesting database...")
    
    try:
        from src.infrastructure.persistence.database import Database
        from src.infrastructure.config.settings import get_settings
        
        settings = get_settings()
        db = Database(settings.database_url)
        
        # Test creating tables
        db.create_tables()
        print("✅ Database tables created")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Database failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoint creation."""
    print("\nTesting API endpoints...")
    
    try:
        from src.presentation.api.app import app
        
        # Check if routes are registered
        routes = [route.path for route in app.routes]
        print(f"✅ API routes: {len(routes)} found")
        
        # Check for key endpoints
        key_endpoints = ["/health", "/ready", "/api/v1/submissions"]
        for endpoint in key_endpoints:
            if any(endpoint in route for route in routes):
                print(f"✅ Found endpoint: {endpoint}")
            else:
                print(f"⚠️ Missing endpoint: {endpoint}")
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoints failed: {e}")
        return False

def test_web_ui():
    """Test web UI setup."""
    print("\nTesting web UI...")
    
    try:
        from src.presentation.web.server import app as web_app
        
        # Check if routes are registered
        routes = [route.path for route in web_app.routes]
        print(f"✅ Web UI routes: {len(routes)} found")
        
        # Check for key pages
        key_pages = ["/", "/upload", "/submissions"]
        for page in key_pages:
            if any(page in route for route in routes):
                print(f"✅ Found page: {page}")
            else:
                print(f"⚠️ Missing page: {page}")
        
        return True
        
    except Exception as e:
        print(f"❌ Web UI failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 PDF Slurper v2 Component Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_configuration,
        test_database,
        test_api_endpoints,
        test_web_ui
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All components working! Ready for deployment.")
        return 0
    else:
        print("⚠️ Some components have issues. Review before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
