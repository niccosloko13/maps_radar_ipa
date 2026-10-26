import Foundation

protocol NavigationCoreSink { func receiveNativeLocation(_ value: NavigationLocation) }
final class NativeLocationBridge { let sink: NavigationCoreSink; init(sink: NavigationCoreSink) { self.sink = sink }; func forward(_ location: NavigationLocation) { sink.receiveNativeLocation(location) } }
