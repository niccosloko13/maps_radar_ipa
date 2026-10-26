import Foundation
import Security

@MainActor final class AuthSession: ObservableObject {
    @Published var isAuthenticated = false
    @Published var hasConsent = false
    @Published var configurationRequired = false
    let deviceInstallID: UUID
    init() { deviceInstallID = KeychainStore.installID(); isAuthenticated = KeychainStore.read("relas.beta.access-token") != nil }
    func store(accessToken: String) { KeychainStore.write(accessToken, key: "relas.beta.access-token"); isAuthenticated = true }
    func signOut() { KeychainStore.delete("relas.beta.access-token"); isAuthenticated = false }
}

enum KeychainStore {
    static func installID() -> UUID { if let value = read("relas.beta.install-id"), let id = UUID(uuidString: value) { return id }; let id = UUID(); write(id.uuidString, key: "relas.beta.install-id"); return id }
    static func read(_ key: String) -> String? { let query: [CFString: Any] = [kSecClass: kSecClassGenericPassword, kSecAttrAccount: key, kSecReturnData: true]; var item: CFTypeRef?; guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess, let data = item as? Data else { return nil }; return String(data: data, encoding: .utf8) }
    static func write(_ value: String, key: String) { let data = Data(value.utf8); delete(key); SecItemAdd([kSecClass: kSecClassGenericPassword, kSecAttrAccount: key, kSecValueData: data, kSecAttrAccessible: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly] as CFDictionary, nil) }
    static func delete(_ key: String) { SecItemDelete([kSecClass: kSecClassGenericPassword, kSecAttrAccount: key] as CFDictionary) }
}
