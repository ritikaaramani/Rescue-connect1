"""
Image Deduplication Module
Uses perceptual hashing to detect duplicate/similar images.
"""

import hashlib
import io
import httpx
from PIL import Image
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
import imagehash


def compute_image_hash(image_bytes: bytes) -> str:
    """
    Compute a perceptual hash of an image.
    Perceptual hashes are similar for visually similar images.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Use average hash + perceptual hash for better accuracy
        ahash = str(imagehash.average_hash(img, hash_size=16))
        phash = str(imagehash.phash(img, hash_size=16))
        return f"{ahash}_{phash}"
    except Exception as e:
        print(f"Error computing image hash: {e}")
        # Fallback to MD5 hash
        return hashlib.md5(image_bytes).hexdigest()


async def fetch_image_bytes(image_url: str) -> bytes:
    """Fetch image bytes from URL."""
    async with httpx.AsyncClient() as client:
        response = await client.get(image_url, timeout=30)
        response.raise_for_status()
        return response.content


def hashes_are_similar(hash1: str, hash2: str, threshold: int = 10) -> bool:
    """
    Compare two hashes and determine if they're similar.
    Lower threshold = stricter matching.
    """
    try:
        # Split combined hash
        parts1 = hash1.split('_')
        parts2 = hash2.split('_')
        
        if len(parts1) == 2 and len(parts2) == 2:
            ahash1 = imagehash.hex_to_hash(parts1[0])
            ahash2 = imagehash.hex_to_hash(parts2[0])
            phash1 = imagehash.hex_to_hash(parts1[1])
            phash2 = imagehash.hex_to_hash(parts2[1])
            
            # Both hashes should be similar
            ahash_diff = ahash1 - ahash2
            phash_diff = phash1 - phash2
            
            return ahash_diff <= threshold and phash_diff <= threshold
        else:
            # Fallback: exact match for MD5 hashes
            return hash1 == hash2
    except Exception as e:
        print(f"Error comparing hashes: {e}")
        return hash1 == hash2


async def check_for_duplicate(
    supabase_client,
    image_url: str,
    hours_window: int = 2
) -> Tuple[bool, Optional[dict]]:
    """
    Check if a similar image was uploaded within the specified time window.
    
    Returns:
        (is_duplicate, existing_post) - If duplicate found, returns the existing post
    """
    try:
        # Fetch and hash the new image
        image_bytes = await fetch_image_bytes(image_url)
        new_hash = compute_image_hash(image_bytes)
        print(f"[DEDUP] New image hash: {new_hash[:30]}...")
        
        # Calculate time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours_window)
        
        # First try: check posts with existing hashes
        response = supabase_client.table("posts")\
            .select("id, image_hash, image_url, status, created_at, caption, location, disaster_type")\
            .gte("created_at", time_threshold.isoformat())\
            .not_.is_("image_url", "null")\
            .neq("image_url", image_url)\
            .execute()
        
        recent_posts = response.data or []
        print(f"[DEDUP] Checking against {len(recent_posts)} recent posts")
        
        # Compare hashes
        for post in recent_posts:
            post_hash = post.get("image_hash")
            
            # If post doesn't have a hash yet, compute it on-the-fly
            if not post_hash and post.get("image_url"):
                try:
                    post_image_bytes = await fetch_image_bytes(post["image_url"])
                    post_hash = compute_image_hash(post_image_bytes)
                    print(f"[DEDUP] Computed hash for post {post['id'][:8]}...: {post_hash[:20]}...")
                    
                    # Store the computed hash for future use (best effort)
                    try:
                        supabase_client.table("posts")\
                            .update({"image_hash": post_hash})\
                            .eq("id", post["id"])\
                            .execute()
                    except:
                        pass  # Ignore if column doesn't exist
                except Exception as e:
                    print(f"[DEDUP] Failed to compute hash for post {post['id']}: {e}")
                    continue
            
            if post_hash and hashes_are_similar(new_hash, post_hash):
                print(f"[DEDUP] ✅ Found duplicate! Post {post['id'][:8]}...")
                return True, post
        
        print(f"[DEDUP] No duplicates found")
        return False, None
        
    except Exception as e:
        print(f"[DEDUP] Error checking for duplicate: {e}")
        return False, None


async def compute_and_store_hash(supabase_client, post_id: str, image_url: str) -> str:
    """
    Compute image hash and store it in the database.
    Returns the computed hash.
    """
    try:
        image_bytes = await fetch_image_bytes(image_url)
        image_hash = compute_image_hash(image_bytes)
        
        # Update the post with the hash
        supabase_client.table("posts")\
            .update({"image_hash": image_hash})\
            .eq("id", post_id)\
            .execute()
        
        return image_hash
    except Exception as e:
        print(f"Error computing/storing hash: {e}")
        return ""
