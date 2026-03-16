"""
input_adapter.py - Adapters for Team 2 and Team 3 Input Formats

Converts input from team members into standardized format for geo_pipeline.

Team 2 Format (text analysis):
{
  "text_labels": ["flood"],
  "text_confidence": 0.5,
  "entities": {
    "locations": ["Kerala"],
    "numbers": ["50"]
  },
  "urgency_score": 0.4,
  "text_model_version": "rule-spacy-v1"
}

Team 3 Format (OCR):
{
  "ocr_text": "Silk Board Bus Stop",
  "ocr_confidence": 0.8
}

Standardized Format for geo_pipeline:
{
  "post_id": "...",
  "caption": "...",           # Combined from Team 2
  "ocr_text": "...",          # From Team 3
  "gps": None,
  "image_path": "...",
  "disaster_type": "...",     # From Team 2 text_labels
  "urgency_score": 0.4        # From Team 2
}
"""

from typing import Dict, Any, Optional, List


def adapt_team2_input(
    team2_data: Dict[str, Any],
    original_caption: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert Team 2's text analysis output to geo pipeline format.
    
    Args:
        team2_data: Output from Team 2's text analysis module
        original_caption: Original post caption (if available)
        
    Returns:
        Partial input dict for geo_pipeline
    """
    # Extract locations from entities
    entities = team2_data.get("entities", {})
    locations = entities.get("locations", [])
    numbers = entities.get("numbers", [])
    
    # Get disaster type
    text_labels = team2_data.get("text_labels", [])
    disaster_type = text_labels[0] if text_labels else "unknown"
    
    # Build caption from locations if original not provided
    if original_caption:
        caption = original_caption
    elif locations:
        # Construct a searchable string from extracted locations
        caption = " ".join(locations)
    else:
        caption = None
    
    return {
        "caption": caption,
        "extracted_locations": locations,  # Direct from Team 2
        "disaster_type": disaster_type,
        "text_confidence": team2_data.get("text_confidence", 0.0),
        "urgency_score": team2_data.get("urgency_score", 0.0),
        "numbers": numbers
    }


def adapt_team3_input(team3_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Team 3's OCR output to geo pipeline format.
    
    Args:
        team3_data: Output from Team 3's OCR module
        
    Returns:
        Partial input dict for geo_pipeline
    """
    return {
        "ocr_text": team3_data.get("ocr_text", ""),
        "ocr_confidence": team3_data.get("ocr_confidence", 0.0)
    }


def combine_team_inputs(
    post_id: str,
    team2_data: Optional[Dict[str, Any]] = None,
    team3_data: Optional[Dict[str, Any]] = None,
    original_caption: Optional[str] = None,
    image_path: Optional[str] = None,
    gps: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Combine inputs from Team 2 and Team 3 into a unified post format.
    
    Args:
        post_id: Unique identifier for the post
        team2_data: Output from Team 2 (text analysis)
        team3_data: Output from Team 3 (OCR)
        original_caption: Original post caption
        image_path: Path to the image file
        gps: GPS coordinates if available
        
    Returns:
        Complete input dict for geo_pipeline.resolve_location()
    """
    result = {
        "post_id": post_id,
        "caption": None,
        "ocr_text": None,
        "gps": gps,
        "image_path": image_path,
        "extracted_locations": [],
        "disaster_type": "unknown",
        "urgency_score": 0.0
    }
    
    # Apply Team 2 data
    if team2_data:
        adapted = adapt_team2_input(team2_data, original_caption)
        result["caption"] = adapted.get("caption")
        result["extracted_locations"] = adapted.get("extracted_locations", [])
        result["disaster_type"] = adapted.get("disaster_type", "unknown")
        result["urgency_score"] = adapted.get("urgency_score", 0.0)
    elif original_caption:
        result["caption"] = original_caption
    
    # Apply Team 3 data
    if team3_data:
        adapted = adapt_team3_input(team3_data)
        result["ocr_text"] = adapted.get("ocr_text")
    
    return result


if __name__ == "__main__":
    # Test with example Team 2 inputs
    print("=== Input Adapter Test ===\n")
    
    team2_examples = [
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
        }
    ]
    
    team3_example = {
        "ocr_text": "Ernakulam District",
        "ocr_confidence": 0.8
    }
    
    for i, team2 in enumerate(team2_examples):
        print(f"Team 2 Input #{i+1}:")
        print(f"  Labels: {team2['text_labels']}")
        print(f"  Locations: {team2['entities']['locations']}")
        
        combined = combine_team_inputs(
            post_id=f"test_{i+1}",
            team2_data=team2,
            team3_data=team3_example if i == 1 else None,
            image_path=None
        )
        
        print(f"  → Combined for geo:")
        print(f"    caption: {combined['caption']}")
        print(f"    ocr_text: {combined['ocr_text']}")
        print(f"    extracted_locations: {combined['extracted_locations']}")
        print(f"    disaster_type: {combined['disaster_type']}")
        print()
