export type ViolationType =
  | 'helmet_violation'
  | 'signal_jump'
  | 'wrong_way'
  | 'speeding'
  | 'no_seatbelt'
  | 'illegal_parking';

export type ViolationStatus =
  | 'detected'
  | 'confirmed'
  | 'rejected'
  | 'evidence_generated'
  | 'sent_to_authority';

export interface Violation {
  id: string;
  camera_id: string;
  violation_type: ViolationType;
  status: ViolationStatus;
  license_plate: string | null;
  confidence: number;
  clip_url: string | null;
  thumbnail_url: string | null;
  evidence_package_url: string | null;
  location: string | null;
  detected_at: string;
  created_at: string;
}

export interface ViolationStats {
  total_violations: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  by_camera: Record<string, number>;
  today_count: number;
  this_week_count: number;
}

export interface Camera {
  id: string;
  name: string;
  stream_url: string;
  location: string | null;
  status: string;
  created_at: string;
}
