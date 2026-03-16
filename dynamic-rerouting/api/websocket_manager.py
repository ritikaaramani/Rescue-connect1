"""
WebSocket Manager for Real-Time Communication

Handles:
- Client connection tracking
- Message broadcasting to dispatch/vehicle/citizen clients
- Connection lifecycle management
"""

import json
import logging
from typing import Dict, Set, Callable, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by role (dispatch, vehicle, citizen)."""

    def __init__(self):
        # Connections grouped by role
        self.dispatch_connections: Set[WebSocket] = set()
        self.vehicle_connections: Dict[str, WebSocket] = {}  # vehicle_id -> connection
        self.citizen_connections: Set[WebSocket] = set()

    async def connect_dispatch(self, websocket: WebSocket):
        """Register dispatch dashboard connection."""
        await websocket.accept()
        self.dispatch_connections.add(websocket)
        logger.info(f"Dispatch connected. Total: {len(self.dispatch_connections)}")

    async def connect_vehicle(self, websocket: WebSocket, vehicle_id: str):
        """Register vehicle app connection."""
        await websocket.accept()
        self.vehicle_connections[vehicle_id] = websocket
        logger.info(f"Vehicle {vehicle_id} connected. Total: {len(self.vehicle_connections)}")

    async def connect_citizen(self, websocket: WebSocket):
        """Register citizen app connection."""
        await websocket.accept()
        self.citizen_connections.add(websocket)
        logger.info(f"Citizen connected. Total: {len(self.citizen_connections)}")

    def disconnect_dispatch(self, websocket: WebSocket):
        """Unregister dispatch connection."""
        self.dispatch_connections.discard(websocket)
        logger.info(f"Dispatch disconnected. Total: {len(self.dispatch_connections)}")

    def disconnect_vehicle(self, vehicle_id: str):
        """Unregister vehicle connection."""
        if vehicle_id in self.vehicle_connections:
            del self.vehicle_connections[vehicle_id]
            logger.info(f"Vehicle {vehicle_id} disconnected. Total: {len(self.vehicle_connections)}")

    def disconnect_citizen(self, websocket: WebSocket):
        """Unregister citizen connection."""
        self.citizen_connections.discard(websocket)
        logger.info(f"Citizen disconnected. Total: {len(self.citizen_connections)}")

    async def broadcast_to_dispatch(self, message: Dict[str, Any]):
        """Send message to all connected dispatch dashboards."""
        message_json = json.dumps(message)
        disconnected = []
        for ws in self.dispatch_connections:
            try:
                await ws.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send to dispatch: {e}")
                disconnected.append(ws)
        
        for ws in disconnected:
            self.disconnect_dispatch(ws)

    async def broadcast_to_vehicles(self, message: Dict[str, Any]):
        """Send message to all connected vehicles."""
        message_json = json.dumps(message)
        disconnected = []
        for vehicle_id, ws in self.vehicle_connections.items():
            try:
                await ws.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send to vehicle {vehicle_id}: {e}")
                disconnected.append(vehicle_id)
        
        for vehicle_id in disconnected:
            self.disconnect_vehicle(vehicle_id)

    async def broadcast_to_vehicle(self, vehicle_id: str, message: Dict[str, Any]):
        """Send message to specific vehicle."""
        if vehicle_id in self.vehicle_connections:
            ws = self.vehicle_connections[vehicle_id]
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send to vehicle {vehicle_id}: {e}")
                self.disconnect_vehicle(vehicle_id)

    async def broadcast_to_citizens(self, message: Dict[str, Any]):
        """Send message to all connected citizens."""
        message_json = json.dumps(message)
        disconnected = []
        for ws in self.citizen_connections:
            try:
                await ws.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send to citizen: {e}")
                disconnected.append(ws)
        
        for ws in disconnected:
            self.disconnect_citizen(ws)

    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Send message to all connected clients (dispatch, vehicles, citizens)."""
        await self.broadcast_to_dispatch(message)
        await self.broadcast_to_vehicles(message)
        await self.broadcast_to_citizens(message)

    async def broadcast_incident_update(self, incident: Dict[str, Any]):
        """Broadcast incident state change (REPORTED, DISPATCHED, etc.) to all."""
        message = {
            "type": "INCIDENT_UPDATE",
            "timestamp": datetime.utcnow().isoformat(),
            "incident": incident
        }
        await self.broadcast_to_all(message)
        logger.info(f"Incident {incident['id']} state: {incident['state']}")

    async def broadcast_vehicle_update(self, vehicle_data: Dict[str, Any]):
        """Broadcast vehicle position update to dispatch and citizens."""
        message = {
            "type": "VEHICLE_UPDATE",
            "timestamp": datetime.utcnow().isoformat(),
            "vehicle": vehicle_data
        }
        await self.broadcast_to_dispatch(message)
        await self.broadcast_to_citizens(message)
        logger.debug(f"Vehicle {vehicle_data['id']} position: ({vehicle_data['lat']}, {vehicle_data['lon']})")

    async def broadcast_reroute(self, vehicle_id: str, route_data: Dict[str, Any]):
        """Broadcast rerouting notification to all."""
        message = {
            "type": "REROUTE",
            "timestamp": datetime.utcnow().isoformat(),
            "vehicle_id": vehicle_id,
            "old_eta_min": route_data.get("old_eta_min"),
            "new_eta_min": route_data.get("new_eta_min"),
            "old_reliability": route_data.get("old_reliability_score"),
            "new_reliability": route_data.get("new_reliability_score"),
            "reason": route_data.get("reason", "Optimization"),
            "new_route": route_data.get("new_route_json")
        }
        await self.broadcast_to_all(message)
        logger.info(f"Vehicle {vehicle_id} rerouted: ETA {route_data.get('old_eta_min')}m → {route_data.get('new_eta_min')}m")

    async def broadcast_witness_report(self, incident_id: str, report_data: Dict[str, Any]):
        """Broadcast new witness report to all."""
        message = {
            "type": "WITNESS_REPORT",
            "timestamp": datetime.utcnow().isoformat(),
            "incident_id": incident_id,
            "report": report_data
        }
        await self.broadcast_to_all(message)
        logger.info(f"Witness report for incident {incident_id}: {report_data.get('text_notes', '(photo)')}")

    async def broadcast_dispatch_message(self, message: str, actor: str = "Dispatch"):
        """Broadcast a dispatch system message."""
        message_obj = {
            "type": "DISPATCH_MESSAGE",
            "timestamp": datetime.utcnow().isoformat(),
            "actor": actor,
            "message": message
        }
        await self.broadcast_to_all(message_obj)
        logger.info(f"Dispatch message from {actor}: {message}")

    def get_connection_stats(self) -> Dict[str, int]:
        """Return connection counts."""
        return {
            "dispatch": len(self.dispatch_connections),
            "vehicles": len(self.vehicle_connections),
            "citizens": len(self.citizen_connections),
            "total": len(self.dispatch_connections) + len(self.vehicle_connections) + len(self.citizen_connections)
        }


# Global instance
manager = ConnectionManager()
