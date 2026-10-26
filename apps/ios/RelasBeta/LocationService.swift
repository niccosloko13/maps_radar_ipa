import CoreLocation

struct NavigationLocation: Codable { let lat: Double; let lon: Double; let accuracy: Double; let speed: Double; let heading: Double?; let timestamp: Date; let source = "ios_core_location" }
final class LocationService: NSObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager(); var onLocation: ((NavigationLocation) -> Void)?; private(set) var activeTrip = false
    override init() { super.init(); manager.delegate = self; manager.activityType = .automotiveNavigation; manager.desiredAccuracy = kCLLocationAccuracyBest }
    func startActiveNavigation() { activeTrip = true; manager.requestWhenInUseAuthorization(); manager.startUpdatingLocation(); manager.startUpdatingHeading() }
    func stopActiveNavigation() { activeTrip = false; manager.stopUpdatingLocation(); manager.stopUpdatingHeading() }
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) { guard activeTrip, let x = locations.last else { return }; onLocation?(NavigationLocation(lat: x.coordinate.latitude, lon: x.coordinate.longitude, accuracy: x.horizontalAccuracy, speed: x.speed, heading: x.course >= 0 ? x.course : nil, timestamp: x.timestamp)) }
}
