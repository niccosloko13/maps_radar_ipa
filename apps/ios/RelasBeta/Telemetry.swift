import Foundation

enum LocationTelemetryLevel: String, Codable { case off = "OFF", summary = "DIAGNOSTIC_SUMMARY", activeTripDebug = "ACTIVE_TRIP_DEBUG" }
struct TelemetryEvent: Codable { let eventID: UUID; let name: String; let occurredAt: Date; let userID: String?; let sessionID: UUID; let tripID: UUID?; let appVersion: String; let buildNumber: String; let platform = "ios"; let osVersion: String; let deviceModel: String; let properties: [String: String] }
actor TelemetryService { private var queue: [TelemetryEvent] = []; private let level: LocationTelemetryLevel = .summary
    func record(_ event: TelemetryEvent) { queue.append(event) }
    func flush(send: @Sendable ([TelemetryEvent]) async throws -> Void) async { guard !queue.isEmpty else { return }; let batch = queue; do { try await send(batch); queue.removeAll() } catch { /* retain offline, bounded queue policy configured by host */ } }
}
struct TripSession: Codable { let tripID: UUID; let userID: String; let startedAt: Date; var endedAt: Date?; let routeID: String?; var gpsLossCount = 0; var rerouteCount = 0; var radarAlertCount = 0; var lateAlertCount = 0; var missedAlertCount = 0 }
