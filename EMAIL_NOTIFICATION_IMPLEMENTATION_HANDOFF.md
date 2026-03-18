# Email Notification Implementation Handoff

Date: 2026-03-18
Owner intent: Send one email (single recipient) when Start Navigation (blue bottom button in Flutter) is clicked, only when pickup and drop coordinates exist. Email must include nearby hospital name and live map link.

## 1) Scope and Non-Scope

### In Scope
- Trigger at Flutter Start Navigation action.
- Single-recipient email only (citizen/reporter).
- Content includes:
  - Pickup and drop coordinates.
  - Nearby hospital name.
  - Live Google Maps directions link.
- Non-blocking behavior: navigation/dispatch must continue even if email fails.

### Out of Scope (Phase 1)
- Multi-recipient emails (To/Cc/Bcc).
- Hospital email contact in DB/schema.
- SMS/push notifications.

## 2) Current Baseline (already in repo)

- ML backend has email endpoint and Resend integration:
  - `user_app/rescue_connect/ml_backend/main.py`
  - `POST /send-notification`
  - current payload fields: `post_id`, `user_id`, `status`, `team_name`, `disaster_type`, `location`
- Flutter blue dispatch/start action exists in:
  - `Traffic_Model1/emergency_routing_flutter/lib/screens/home_screen.dart`
  - callback: `_onDispatch()`
- Authority dashboard already calls `/send-notification` after status changes:
  - `user_app/rescue_connect/authority/src/components/DispatchView.jsx`
- Flutter incident feed already carries destination hospital name (`destLabel`) and route polyline in results.

## 3) Implementation Tasks

### A. Flutter Trigger and Payload Build

Files:
- `Traffic_Model1/emergency_routing_flutter/lib/screens/home_screen.dart`
- `Traffic_Model1/emergency_routing_flutter/lib/services/backend_service.dart`
- `Traffic_Model1/emergency_routing_flutter/lib/providers/emergency_requests_provider.dart`
- `Traffic_Model1/emergency_routing_flutter/lib/models/route_model.dart`

Tasks:
1. Rename the blue action UI text to `START NAVIGATION` (if product wants exact text).
2. In `_onDispatch()` gate notification trigger on valid route coordinates:
   - `result != null`
   - `result.polyline.isNotEmpty`
   - pickup = `result.polyline.first`
   - drop = `result.polyline.last`
3. Capture incident context for recipient resolution:
   - Add `reporterUserId` to `EmergencyRequest` model.
   - Populate it from Supabase `posts.user_id` in provider/service mapping.
4. Build payload data from available context:
   - `post_id` = incident id
   - `user_id` = reporterUserId
   - `status` = `assigned` (or agreed routing-start status)
   - `team_name` from suggested vehicle label
   - `disaster_type` from incident/raw type
   - `location` from origin label
   - `pickup_lat`, `pickup_lon`, `drop_lat`, `drop_lon`
   - `nearby_hospital_name` from destination label
   - `map_link` = Google directions URL
5. Add a dedicated service method to call ML endpoint:
   - `sendRoutingStartNotification(...)` in backend service.
   - Try ML base URL(s) and throw clear error if all fail.
6. Add idempotency on client side to avoid duplicate emails on rapid taps:
   - Create and cache idempotency key per routing session.
   - Do not resend for same key.
7. Make notification call non-blocking:
   - Dispatch/navigation success should not be rolled back.
   - On email failure, show warning snackbar only.

### B. ML Backend Request Contract and Validation

File:
- `user_app/rescue_connect/ml_backend/main.py`

Tasks:
1. Extend `NotificationRequest` with optional fields:
   - `pickup_lat`, `pickup_lon`, `drop_lat`, `drop_lon`
   - `nearby_hospital_name`
   - `map_link`
   - `idempotency_key`
   - `single_recipient_only` (default true)
   - optional `recipient_email`, `recipient_emails`
2. Enforce single-recipient mode:
   - reject requests that provide multiple recipients.
   - continue using one resolved user email from `user_id` by default.
3. Update email template body:
   - Include route coordinates line.
   - Include nearby hospital name line.
   - Include live map link line.
4. Keep endpoint non-blocking for dispatch flow:
   - Preserve current pattern returning success envelope even if send fails.

### C. Optional Authority Parity (same email content)

File:
- `user_app/rescue_connect/authority/src/components/DispatchView.jsx`

Tasks:
1. If authority flow should send same enriched payload, update request body to include:
   - hospital name (from selected destination hospital)
   - map link if pickup/drop available
2. Keep recipient single-user only.

## 4) Payload Contract (Phase 1)

Request to `POST /send-notification`:

```json
{
  "post_id": "post-123",
  "user_id": "uuid-user-id",
  "status": "assigned",
  "team_name": "AMBULANCE UP-14-342",
  "disaster_type": "medical",
  "location": "MG Road, Indore",
  "pickup_lat": 22.71957,
  "pickup_lon": 75.85773,
  "drop_lat": 22.75330,
  "drop_lon": 75.89370,
  "nearby_hospital_name": "State General Hospital",
  "map_link": "https://www.google.com/maps/dir/?api=1&origin=22.71957,75.85773&destination=22.75330,75.89370&travelmode=driving",
  "idempotency_key": "post-123:user-uuid:22.71957,75.85773:22.75330,75.89370",
  "single_recipient_only": true
}
```

## 5) Acceptance Criteria

1. Clicking Start Navigation with valid pickup/drop sends exactly one notification request.
2. Email is sent to one user only (citizen/reporter).
3. Email body contains:
   - route coordinates
   - nearby hospital name
   - clickable Google Maps link
4. Repeated rapid taps do not create duplicate sends for the same route event.
5. If Resend/API fails, navigation/dispatch still succeeds and user sees warning only.

## 6) Test Plan

### Manual
1. Create/select incident with known `user_id` and route.
2. Trigger Start Navigation in Flutter.
3. Verify backend log shows one notification request.
4. Verify recipient mailbox content.
5. Simulate ML backend failure and verify navigation still proceeds.

### Automated (recommended)
- Unit test for payload builder in Flutter service.
- Unit test for single-recipient validation in ML backend.
- Integration test for idempotency behavior.

## 7) Environment Requirements

- `RESEND_API_KEY` set for ML backend process.
- Supabase admin access available to resolve `user_id -> email`.
- ML backend URL must be reachable from Flutter app.

## 8) Risks and Notes

- If incident context lacks `user_id`, notification must be skipped with log (do not block navigation).
- Sandbox Resend accounts may only deliver to limited verified/test recipients.
- Keep this release single-recipient by hard validation to prevent accidental broadcast.
