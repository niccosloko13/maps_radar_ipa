import Foundation
struct FeatureFlags: Codable { var iosNativeLocation = true; var precisionEngineV2 = true; var adaptiveCamera = true; var roadMode = true; var radarVoice = true; var routeProgress = true; var debugTripLogging = false; var newMapIcons = false }
actor FeatureFlagService { private(set) var flags = FeatureFlags(); func applyRemote(_ value: FeatureFlags?) { if let value { flags = value } } }
