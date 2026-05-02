import numpy as np
import supervision as sv


class VehicleTracker:
    def __init__(self):
        self.tracker = sv.ByteTrack()
        self.tracks: dict[int, list[dict]] = {}

    def update(self, detections: list[dict], frame_id: int) -> list[dict]:
        if not detections:
            return []

        bboxes = np.array([d["bbox"] for d in detections])
        confidences = np.array([d["confidence"] for d in detections])
        class_ids = np.array([d["class_id"] for d in detections])

        sv_detections = sv.Detections(
            xyxy=bboxes,
            confidence=confidences,
            class_id=class_ids,
        )

        tracked = self.tracker.update_with_detections(sv_detections)

        results = []
        if tracked.tracker_id is not None:
            for i, tracker_id in enumerate(tracked.tracker_id):
                track_data = {
                    "tracker_id": int(tracker_id),
                    "bbox": tracked.xyxy[i].tolist(),
                    "confidence": float(tracked.confidence[i]),
                    "class_id": int(tracked.class_id[i]),
                    "frame_id": frame_id,
                }
                results.append(track_data)

                if tracker_id not in self.tracks:
                    self.tracks[tracker_id] = []
                self.tracks[tracker_id].append(track_data)

        return results

    def get_track_history(self, tracker_id: int) -> list[dict]:
        return self.tracks.get(tracker_id, [])

    def get_track_direction(self, tracker_id: int) -> str | None:
        history = self.get_track_history(tracker_id)
        if len(history) < 5:
            return None

        start_center_y = (history[0]["bbox"][1] + history[0]["bbox"][3]) / 2
        end_center_y = (history[-1]["bbox"][1] + history[-1]["bbox"][3]) / 2

        if end_center_y < start_center_y:
            return "up"
        return "down"

    def reset(self):
        self.tracker = sv.ByteTrack()
        self.tracks.clear()
