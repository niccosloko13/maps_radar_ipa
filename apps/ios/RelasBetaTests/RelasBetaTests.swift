import XCTest
@testable import RelasBeta
final class RelasBetaTests: XCTestCase {
    func testLocationContractUsesCoreLocationSource() { let value = NavigationLocation(lat: 1, lon: 2, accuracy: 3, speed: 4, heading: 5, timestamp: .now); XCTAssertEqual(value.source, "ios_core_location") }
    func testDefaultsKeepRadarAndCameraEnabled() async { let flags = await FeatureFlagService().flags; XCTAssertTrue(flags.adaptiveCamera); XCTAssertTrue(flags.radarVoice) }
}
