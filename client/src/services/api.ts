/**
 * Accident SOS Backend API Service
 * Implements endpoints per docs/api_documentation.md
 */

export interface HealthResponse {
  status: string
  message: string
}

export interface SensorDataPayload {
  device_id: string
  sos_type?: string // "ACCIDENT", "NONE", "MANUAL"
  accel_x: number
  accel_y: number
  accel_z: number
  gyro_x: number
  gyro_y: number
  gyro_z: number
  impact_g: number
  vibration: boolean
  temperature: number
  humidity: number
  gps_lat: number
  gps_lon: number
  gps_speed_kmph: number
  gps_fix: boolean
  timestamp?: number
  battery_pct?: number
}

export interface DeviceDto {
  device_id: string
  status: "ok" | "unreachable" | "sos_confirmed" | "impact_detected" | string
  last_heartbeat_time: number
  last_gps_lat: number
  last_gps_lon: number
  battery_pct: number
}

export interface DevicesResponse {
  devices: DeviceDto[]
}

export interface EventDto {
  id: number
  device_id: string
  timestamp: number
  type: string
  payload: Record<string, unknown>
}

export interface EventsResponse {
  events: EventDto[]
}

export interface AcknowledgeResponse {
  status: string
  message: string
}

export interface RawSensorData {
  sensor_type: string
  readings: number[]
  timestamp: number
  [key: string]: unknown
}

const API_BASE = "/api"

export const api = {
  /**
   * GET /api/health
   */
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE}/health`)
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`)
    return res.json()
  },

  /**
   * GET /api/devices
   */
  async getDevices(): Promise<DevicesResponse> {
    const res = await fetch(`${API_BASE}/devices`)
    if (!res.ok) throw new Error(`Failed to fetch devices: ${res.statusText}`)
    return res.json()
  },

  /**
   * GET /api/events?limit={limit}
   */
  async getEvents(limit = 50): Promise<EventsResponse> {
    const res = await fetch(`${API_BASE}/events?limit=${limit}`)
    if (!res.ok) throw new Error(`Failed to fetch events: ${res.statusText}`)
    return res.json()
  },

  /**
   * POST /api/devices/{device_id}/acknowledge
   */
  async acknowledgeDevice(deviceId: string): Promise<AcknowledgeResponse> {
    const res = await fetch(`${API_BASE}/devices/${encodeURIComponent(deviceId)}/acknowledge`, {
      method: "POST",
    })
    if (!res.ok) throw new Error(`Failed to acknowledge device ${deviceId}: ${res.statusText}`)
    return res.json()
  },

  /**
   * POST /api/sensor
   */
  async postSos(payload: SensorDataPayload): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/sensor`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(`Failed to post SOS data: ${res.statusText}`)
    return res.json()
  },

  /**
   * GET /api/sensor
   */
  async getRawSensor(): Promise<RawSensorData[] | string[]> {
    const res = await fetch(`${API_BASE}/sensor`)
    if (!res.ok) throw new Error(`Failed to fetch raw sensor data: ${res.statusText}`)
    return res.json()
  },

  /**
   * POST /api/sensor
   */
  async postRawSensor(payload: RawSensorData): Promise<{ message: string; "Data : ": RawSensorData }> {
    const res = await fetch(`${API_BASE}/sensor`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(`Failed to post raw sensor data: ${res.statusText}`)
    return res.json()
  },
}
