from __future__ import annotations

import numpy as np

from aeris.models import Detection, Track


class MultiObjectTracker:
    """Deterministic association baseline with world- and image-space kinematics."""

    def __init__(self, association_distance_m: float = 20.0, max_missed: int = 3) -> None:
        self.association_distance_m = association_distance_m
        self.max_missed = max_missed
        self._tracks: dict[str, Track] = {}
        self._next_id = 1

    def update(self, detections: list[Detection], timestamp: float) -> list[Track]:
        available = {k for k in self._tracks}
        updated: set[str] = set()
        for detection in detections:
            if detection.position is None:
                continue
            position = np.asarray(detection.position, dtype=float)
            match = self._nearest(position, available)
            if match is None:
                match = f"track-{self._next_id:03d}"
                self._next_id += 1
                self._tracks[match] = Track(
                    match,
                    detection.object_class,
                    detection.bbox_xyxy,
                    position.copy(),
                    np.zeros(3),
                    (0.0, 0.0),
                    detection.confidence,
                    1,
                    0,
                    timestamp,
                    [position.copy()],
                )
            else:
                track = self._tracks[match]
                dt = max(timestamp - track.timestamp, 1e-6)
                track.velocity = (position - track.position) / dt
                old_center = self._center(track.bbox_xyxy)
                new_center = self._center(detection.bbox_xyxy)
                track.image_velocity_px_s = (
                    (new_center[0] - old_center[0]) / dt,
                    (new_center[1] - old_center[1]) / dt,
                )
                track.object_class = detection.object_class
                track.bbox_xyxy = detection.bbox_xyxy
                track.position = position.copy()
                track.confidence = detection.confidence
                track.age += 1
                track.missed_frames = 0
                track.timestamp = timestamp
                track.history.append(position.copy())
                available.remove(match)
            updated.add(match)
        for track_id in list(self._tracks):
            if track_id not in updated:
                self._tracks[track_id].missed_frames += 1
                if self._tracks[track_id].missed_frames > self.max_missed:
                    del self._tracks[track_id]
        return list(self._tracks.values())

    def _nearest(self, position: np.ndarray, candidates: set[str]) -> str | None:
        if not candidates:
            return None
        track_id = min(
            candidates, key=lambda key: np.linalg.norm(self._tracks[key].position - position)
        )
        if np.linalg.norm(self._tracks[track_id].position - position) > self.association_distance_m:
            return None
        return track_id

    @staticmethod
    def _center(box: tuple[float, float, float, float]) -> tuple[float, float]:
        return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)
