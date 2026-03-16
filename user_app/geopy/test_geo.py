"""
test_geo.py - Test script for the Geolocation Module

This script demonstrates how to:
1. Test with Team 2 input format
2. Test with an image
3. Test with manual inputs
"""

import json
from geo.geo_pipeline import resolve_location
from geo.input_adapter import combine_team_inputs


def test_with_team2_format():
    """Test using Team 2's actual output format."""
    print("=" * 60)
    print("TEST 1: Using Team 2 Format")
    print("=" * 60)
    
    # Example inputs from Team 2
    team2_inputs = [
        {
            "text_labels": ["fire"],
            "text_confidence": 0.5,
            "entities": {"locations": [], "numbers": []},
            "urgency_score": 0.4,
            "text_model_version": "rule-spacy-v1"
        },
        {
            "text_labels": ["flood"],
            "text_confidence": 0.5,
            "entities": {"locations": ["Kerala"], "numbers": ["50"]},
            "urgency_score": 0.4,
            "text_model_version": "rule-spacy-v1"
        },
        {
            "text_labels": ["flood"],
            "text_confidence": 0.7,
            "entities": {"locations": ["Silk Board", "Bangalore"], "numbers": []},
            "urgency_score": 0.6,
            "text_model_version": "rule-spacy-v1"
        }
    ]
    
    # Example Team 3 OCR output
    team3_ocr = {
        "ocr_text": "Ernakulam District Office",
        "ocr_confidence": 0.8
    }
    
    for i, team2 in enumerate(team2_inputs):
        print(f"\n--- Test Case {i+1} ---")
        print(f"Team 2 Labels: {team2['text_labels']}")
        print(f"Team 2 Locations: {team2['entities']['locations']}")
        
        # Combine inputs
        post = combine_team_inputs(
            post_id=f"test_{i+1}",
            team2_data=team2,
            team3_data=team3_ocr if i == 1 else None,  # Only add OCR for case 2
            image_path=None
        )
        
        # Resolve location
        result = resolve_location(post)
        
        print(f"\nResult:")
        print(f"  Location: {result['location'] or 'NOT FOUND'}")
        if result['latitude']:
            print(f"  Coordinates: ({result['latitude']:.4f}, {result['longitude']:.4f})")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Method: {result['method']}")
        print(f"  Ambiguous: {result['is_ambiguous']}")


def test_with_image(image_path: str):
    """Test with an actual image file."""
    print("\n" + "=" * 60)
    print("TEST 2: With Image Analysis")
    print("=" * 60)
    
    post = {
        "post_id": "image_test",
        "caption": "Flooding in residential area",
        "ocr_text": "Koramangala",
        "image_path": image_path,
        "gps": None
    }
    
    print(f"\nImage: {image_path}")
    print(f"Caption: {post['caption']}")
    print(f"OCR Text: {post['ocr_text']}")
    
    result = resolve_location(post)
    
    print(f"\nResult:")
    print(f"  Location: {result['location'] or 'NOT FOUND'}")
    if result['latitude']:
        print(f"  Coordinates: ({result['latitude']:.4f}, {result['longitude']:.4f})")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Method: {result['method']}")
    
    if result['scene_analysis']:
        sa = result['scene_analysis']
        print(f"  Scene Type: {sa.get('scene_type')}")
        print(f"  Scene Confidence: {sa.get('confidence')}")


def test_direct():
    """Test with direct input format."""
    print("\n" + "=" * 60)
    print("TEST 3: Direct Input")
    print("=" * 60)
    
    posts = [
        {
            "post_id": "direct_1",
            "caption": "People stranded near Hebbal flyover",
            "ocr_text": "Hebbal Junction",
            "extracted_locations": ["Hebbal", "Bangalore"],  # From Team 2
            "gps": None,
            "image_path": None
        },
        {
            "post_id": "direct_2",
            "caption": "Flood waters rising",
            "ocr_text": "",
            "extracted_locations": [],  # No locations found
            "gps": None,
            "image_path": None
        }
    ]
    
    for post in posts:
        print(f"\n--- {post['post_id']} ---")
        print(f"Caption: {post['caption']}")
        print(f"OCR: {post['ocr_text'] or '(none)'}")
        print(f"Extracted Locations: {post['extracted_locations']}")
        
        result = resolve_location(post)
        
        print(f"\nResult:")
        print(f"  Location: {result['location'] or 'NOT FOUND'}")
        if result['latitude']:
            print(f"  Coordinates: ({result['latitude']:.4f}, {result['longitude']:.4f})")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Ambiguous: {result['is_ambiguous']}")


if __name__ == "__main__":
    import sys
    
    # Run Team 2 format tests
    test_with_team2_format()
    
    # Run direct tests
    test_direct()
    
    # If image path provided, test with image
    if len(sys.argv) > 1:
        test_with_image(sys.argv[1])
    else:
        print("\n" + "=" * 60)
        print("TIP: To test with an image, run:")
        print("  python test_geo.py <path_to_image>")
        print("=" * 60)
