from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.models import Device, DeviceTimelapseSnapshot
from app.services.images import list_recent_images_for_device, list_timelapse_images_for_device
from app.services.storage import image_client_url


TIMELAPSE_MIN_FRAME_MS = 50
TIMELAPSE_MAX_FRAME_MS = 30_000


def get_timelapse_snapshot(
    session: Session,
    device_id: int,
    *,
    days: int,
    interval_minutes: int,
    max_frames: int,
    target_duration_seconds: int,
) -> DeviceTimelapseSnapshot | None:
    return session.scalar(
        select(DeviceTimelapseSnapshot)
        .where(DeviceTimelapseSnapshot.device_id == device_id)
        .where(DeviceTimelapseSnapshot.window_days == days)
        .where(DeviceTimelapseSnapshot.interval_minutes == interval_minutes)
        .where(DeviceTimelapseSnapshot.max_frames == max_frames)
        .where(DeviceTimelapseSnapshot.target_duration_seconds == target_duration_seconds)
        .limit(1)
    )


def empty_timelapse_payload(
    *,
    device_id: int,
    days: int,
    interval_minutes: int,
    target_duration_seconds: int,
    playback_frame_ms: int | None = None,
) -> dict[str, Any]:
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(days=days)
    return {
        "device_id": device_id,
        "window_start": window_start,
        "window_end": window_end,
        "interval_minutes": interval_minutes,
        "target_duration_seconds": target_duration_seconds,
        "playback_frame_ms": playback_frame_ms
        if playback_frame_ms is not None
        else timelapse_playback_frame_ms(0, target_duration_seconds),
        "total_image_count": 0,
        "frame_count": 0,
        "frames": [],
    }


def timelapse_snapshot_payload(
    snapshot: DeviceTimelapseSnapshot,
    *,
    playback_frame_ms: int | None = None,
) -> dict[str, Any]:
    return {
        "device_id": snapshot.device_id,
        "window_start": snapshot.window_start,
        "window_end": snapshot.window_end,
        "interval_minutes": snapshot.interval_minutes,
        "target_duration_seconds": snapshot.target_duration_seconds,
        "playback_frame_ms": playback_frame_ms if playback_frame_ms is not None else snapshot.playback_frame_ms,
        "total_image_count": snapshot.total_image_count,
        "frame_count": snapshot.frame_count,
        "frames": snapshot.frames,
    }


def refresh_device_timelapse_snapshot(
    *,
    session: Session,
    request: Request,
    device: Device,
    settings: Settings,
    days: int = 7,
    interval_minutes: int = 5,
    max_frames: int = 168,
    target_duration_seconds: int = 30,
) -> DeviceTimelapseSnapshot:
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(days=days)
    images, total_image_count = list_timelapse_images_for_device(
        session,
        device.id,
        start=window_start,
        end=window_end,
        interval_minutes=interval_minutes,
        max_frames=max_frames,
    )
    frames = [
        {
            "id": image.id,
            "content_url": image_client_url(image, request, settings),
            "timestamp": image.timestamp.isoformat(),
            "source_hardware_device_id": image.source_hardware_device_id,
        }
        for image in images
    ]
    snapshot = get_timelapse_snapshot(
        session,
        device.id,
        days=days,
        interval_minutes=interval_minutes,
        max_frames=max_frames,
        target_duration_seconds=target_duration_seconds,
    )
    if snapshot is None:
        snapshot = DeviceTimelapseSnapshot(
            device_id=device.id,
            window_days=days,
            interval_minutes=interval_minutes,
            max_frames=max_frames,
            target_duration_seconds=target_duration_seconds,
            window_start=window_start,
            window_end=window_end,
            playback_frame_ms=timelapse_playback_frame_ms(len(frames), target_duration_seconds),
            total_image_count=total_image_count,
            frame_count=len(frames),
            frames=frames,
        )
        session.add(snapshot)

    snapshot.window_start = window_start
    snapshot.window_end = window_end
    snapshot.playback_frame_ms = timelapse_playback_frame_ms(len(frames), target_duration_seconds)
    snapshot.total_image_count = total_image_count
    snapshot.frame_count = len(frames)
    snapshot.frames = frames
    snapshot.latest_image_id = list_recent_images_for_device(session, device.id, limit=1)[0].id if total_image_count else None
    snapshot.refreshed_at = window_end
    snapshot.expires_at = window_end + timedelta(seconds=settings.image_signed_url_ttl_seconds)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def timelapse_playback_frame_ms(frame_count: int, target_duration_seconds: int) -> int:
    desired_frame_ms = round((target_duration_seconds * 1000) / max(frame_count, 1))
    return min(TIMELAPSE_MAX_FRAME_MS, max(TIMELAPSE_MIN_FRAME_MS, desired_frame_ms))
