import SwiftUI

@main struct RelasBetaApp: App {
    @StateObject private var session = AuthSession()
    var body: some Scene { WindowGroup { RootView().environmentObject(session) } }
}

struct RootView: View {
    @EnvironmentObject var session: AuthSession
    var body: some View {
        Group {
            if !session.isAuthenticated { AuthGateView() }
            else if !session.hasConsent { ConsentView() }
            else { NavigationHostView() }
        }
    }
}

struct AuthGateView: View { @EnvironmentObject var session: AuthSession; var body: some View { VStack { Text("RELAS Beta").font(.title); Text("Entre para participar do beta."); Button("Entrar (configuração do backend necessária)") { session.configurationRequired = true } }.alert("CONFIG_REQUIRED", isPresented: $session.configurationRequired) { Button("OK", role: .cancel) {} } message: { Text("O backend atual não fornece autenticação de usuários beta.") } } }
struct ConsentView: View { @EnvironmentObject var session: AuthSession; var body: some View { VStack { Text("Privacidade do beta").font(.title2); Text("Diagnósticos e localização somente durante navegação ativa."); Button("Concordar") { session.hasConsent = true } } } }
struct NavigationHostView: View { @State private var diagnostics = false; var body: some View { VStack { Text("Renderer atual via bridge; mapa nativo não faz parte desta fundação."); Button("Diagnósticos") { diagnostics = true } }.sheet(isPresented: $diagnostics) { DiagnosticsView() } } }
struct DiagnosticsView: View { private let id = UUID(); var body: some View { NavigationStack { List { LabeledContent("App", value: "0.1.0 (build configurado em CI)"); LabeledContent("Session ID", value: id.uuidString); LabeledContent("Trip ID", value: "sem viagem ativa"); LabeledContent("Location", value: "verifique durante navegação"); LabeledContent("API", value: "beta configurada externamente"); LabeledContent("Telemetry queue", value: "local"); Section { Button("Reportar problema") {} } footer: { Text("O pacote não contém tokens, senhas ou localização bruta.") } }.navigationTitle("Diagnósticos") } } }
