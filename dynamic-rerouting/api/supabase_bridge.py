"""
Supabase Bridge — polls Supabase for new disaster posts and creates
incidents in the emergency routing system.

Environment variables required (optional — falls back to mock mode):
  SUPABASE_URL          e.g. https://xxxx.supabase.co
  SUPABASE_SERVICE_KEY  service role key (bypasses RLS)
"""
import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ROUTING_API_URL = "http://127.0.0.1:9000"

# Severity threshold above which a post auto-creates an incident
AUTO_INCIDENT_SEVERITY = 6

# Polling interval in seconds
POLL_INTERVAL = 10


class SupabaseBridge:
    """Bridges Supabase disaster posts to the emergency routing system."""

    def __init__(self):
        self._running = False
        self._processed_post_ids: set = set()
        self._mock_mode = not (SUPABASE_URL and SUPABASE_SERVICE_KEY)
        if self._mock_mode:
            logger.warning(
                "SupabaseBridge: SUPABASE_URL or SUPABASE_SERVICE_KEY not set — "
                "running in mock mode (no real Supabase calls)."
            )

    # ── Public API ───────────────────────────────────────────────────────────

    async def start(self):
        """Start the background polling loop."""
        self._running = True
        asyncio.create_task(self._poll_loop())
        logger.info("SupabaseBridge started (interval=%ds)", POLL_INTERVAL)

    async def stop(self):
        """Stop the polling loop."""
        self._running = False
        logger.info("SupabaseBridge stopped")

    async def update_post_dispatch_status(
        self, post_id: str, status: str = "dispatched"
    ) -> bool:
        """Update dispatch_status on a Supabase post (called when a vehicle is dispatched)."""
        if self._mock_mode:
            logger.info("[mock] update_post_dispatch_status(%s, %s)", post_id, status)
            return True
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.patch(
                    f"{SUPABASE_URL}/rest/v1/posts?id=eq.{post_id}",
                    headers=self._headers(),
                    json={"dispatch_status": status},
                )
                resp.raise_for_status()
                return True
        except Exception as exc:
            logger.error("Failed to update post %s: %s", post_id, exc)
            return False

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    async def _poll_loop(self):
        while self._running:
            try:
                await self._process_pending_posts()
            except Exception as exc:
                logger.error("SupabaseBridge poll error: %s", exc)
            await asyncio.sleep(POLL_INTERVAL)

    async def _process_pending_posts(self):
        posts = await self._fetch_pending_posts()
        for post in posts:
            post_id = str(post.get("id", ""))
            if post_id in self._processed_post_ids:
                continue
            severity = int(post.get("severity") or 0)
            if severity >= AUTO_INCIDENT_SEVERITY:
                await self._create_incident_from_post(post)
            self._processed_post_ids.add(post_id)

    async def _fetch_pending_posts(self):
        if self._mock_mode:
            return []  # Nothing to process in mock mode
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{SUPABASE_URL}/rest/v1/posts",
                    headers=self._headers(),
                    params={
                        "dispatch_status": "eq.pending",
                        "order": "created_at.desc",
                        "limit": "20",
                    },
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.warning("Could not fetch posts from Supabase: %s", exc)
            return []

    async def _create_incident_from_post(self, post: Dict[str, Any]):
        """Convert a Supabase disaster post into a routing system incident."""
        post_id = str(post.get("id", ""))
        location = post.get("location") or {}
        lat = float(location.get("lat") or location.get("latitude") or 22.7533)
        lon = float(location.get("lon") or location.get("longitude") or 75.8937)
        severity = int(post.get("severity") or 5)
        caption = str(post.get("caption") or "Disaster reported via citizen app")

        # Determine incident type from AI analysis or caption
        ai_analysis = post.get("ai_analysis") or {}
        incident_type = ai_analysis.get("disaster_type") or _infer_type(caption)

        incident_payload = {
            "id": f"SUP-{post_id[:8]}",
            "reporter_id": str(post.get("user_id", "citizen_app")),
            "location": [lat, lon],
            "type": incident_type,
            "severity": severity,
            "timestamp": post.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "state": "REPORTED",
        }

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{ROUTING_API_URL}/incident/report",
                    json=incident_payload,
                )
                resp.raise_for_status()
                logger.info(
                    "Created incident SUP-%s from Supabase post (severity=%d, type=%s)",
                    post_id[:8], severity, incident_type,
                )
        except Exception as exc:
            logger.error("Failed to create incident from post %s: %s", post_id, exc)


def _infer_type(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["fire", "burn", "flame"]):
        return "fire"
    if any(w in text_lower for w in ["flood", "water", "rain"]):
        return "flood"
    if any(w in text_lower for w in ["accident", "crash", "collision"]):
        return "accident"
    if any(w in text_lower for w in ["medical", "heart", "injury", "hurt"]):
        return "medical"
    return "disaster"


# Global singleton
supabase_bridge = SupabaseBridge()
