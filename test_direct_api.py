#!/usr/bin/env python3
"""Test the API directly without going through HTTP."""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.application.container import Container
from src.presentation.api.v1.routers.submissions import get_submission_samples
from fastapi import Query

class FakeRequest:
    """Fake request for testing."""
    pass

async def test():
    # Create container
    container = Container()
    
    # Test parameters
    submission_id = "97c30e3a-9c8b-44fd-85ad-5dc1fcaa4029"
    
    print(f"Testing get_submission_samples for: {submission_id}")
    print("="*60)
    
    # Call the function directly
    result = await get_submission_samples(
        submission_id=submission_id,
        limit=100,
        offset=0,
        container=container
    )
    
    print(f"Result type: {type(result)}")
    print(f"Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
    
    if isinstance(result, dict):
        print(f"\nTotal samples: {result.get('total', 0)}")
        print(f"Items returned: {len(result.get('items', []))}")
        
        if 'debug' in result:
            print("\nDebug info:")
            for k, v in result.get('debug', {}).items():
                print(f"  {k}: {v}")
        
        if 'error' in result:
            print(f"\nError: {result['error']}")
            
        if result.get('items'):
            print("\nFirst 3 samples:")
            for item in result['items'][:3]:
                print(f"  - {item.get('name')}: vol={item.get('volume_ul')}, nano={item.get('nanodrop_ng_per_ul')}")

asyncio.run(test())
