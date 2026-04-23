# Add Proactive Notifications

## Overview

System-initiated push notifications via WebSocket for real-time updates.

## Motivation

Users need real-time updates even without polling. Support notifications for:
- Agent task completion
- System announcements
- SLA breach warnings

## Specification

### Core Features

1. **Notification Types**
   - Task completion events
   - System announcements
   - SLA warning (response time exceeded)

2. **Delivery**
   - WebSocket push to connected clients
   - Store notification for offline users
   - Retry on delivery failure

3. **Client API**
   - Subscribe to notification channel
   - Handle notification events
   - Display in UI

### File Changes

- `chat_service/services/notifications.py`: Notification service
- `chat_service/routes/ws_chat.py`: Notification channel

## Acceptance Criteria

- [ ] Notifications delivered within 100ms
- [ ] Offline users receive on reconnect
- [ ] Notification types extensible