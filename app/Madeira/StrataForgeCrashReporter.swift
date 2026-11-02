import Foundation
import SwiftUI

/// Crash-suspect and runtime error journal. No personal data or raw game logs.
final class StrataForgeCrashReporter: ObservableObject {
    static let shared = StrataForgeCrashReporter()
    @Published var enabled = UserDefaults.standard.bool(forKey: "sf.reports.enabled") {
        didSet { UserDefaults.standard.set(enabled, forKey: "sf.reports.enabled") }
    }
    @Published private(set) var lastStatus = "Reports saved locally"
    @Published var relayURL = UserDefaults.standard.string(forKey: "sf.reports.relay") ?? "" {
        didSet { UserDefaults.standard.set(relayURL, forKey: "sf.reports.relay") }
    }
    private let key = "sf.session.open"
    private let journalKey = "sf.reports.pending"
    private let queue = DispatchQueue(label: "sf.crash.journal")
    private init() {}
    func launch() {
        queue.async {
            if UserDefaults.standard.bool(forKey: self.key) {
                self.append("unexpected_previous_exit")
            }
            UserDefaults.standard.set(true, forKey: self.key)
            DispatchQueue.main.async { self.sendQueued() }
        }
    }
    func background() {
        queue.async { UserDefaults.standard.set(false, forKey: self.key) }
    }
    func foreground() {
        queue.async { UserDefaults.standard.set(true, forKey: self.key) }
    }
    func record(_ code: String) {
        let allowed = ["memory_warning", "wine_error", "jit_error", "graphics_error", "steam_error"]
        guard allowed.contains(code) else { return }
        queue.async { self.append(code) }
    }
    private func append(_ code: String) {
        var entries = UserDefaults.standard.stringArray(forKey: journalKey) ?? []
        entries.append("\(Int(Date().timeIntervalSince1970)) \(code)")
        UserDefaults.standard.set(Array(entries.suffix(40)), forKey: journalKey)
        DispatchQueue.main.async { self.sendQueued() }
    }
    func sendQueued() {
        guard enabled, let url = URL(string: relayURL), url.scheme == "https",
              url.host != nil, !url.path.isEmpty else {
            lastStatus = "Configure an HTTPS relay to enable uploads"
            return
        }
        let entries = UserDefaults.standard.stringArray(forKey: journalKey) ?? []
        guard !entries.isEmpty else { return }
        let payload: [String: Any] = ["schema": 1, "kind": "madeira-diagnostic-events", "events": entries.suffix(40)]
        guard let data = try? JSONSerialization.data(withJSONObject: payload), data.count < 8192 else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 12
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = data
        let sent = entries
        URLSession.shared.dataTask(with: request) { _, response, error in
            DispatchQueue.main.async {
                guard error == nil, (response as? HTTPURLResponse)?.statusCode == 202 else {
                    self.lastStatus = "Upload failed; events retained for retry"
                    return
                }
                var remaining = UserDefaults.standard.stringArray(forKey: self.journalKey) ?? []
                if remaining.starts(with: sent) { remaining.removeFirst(sent.count) }
                UserDefaults.standard.set(remaining, forKey: self.journalKey)
                self.lastStatus = "Relay accepted diagnostic events"
            }
        }.resume()
    }
    var sanitizedReport: String {
        let entries = UserDefaults.standard.stringArray(forKey: journalKey) ?? []
        return "Madeira + StrataForge diagnostics (no raw game logs)\n" + entries.joined(separator: "\n")
    }
    func clearLocalReport() {
        UserDefaults.standard.removeObject(forKey: journalKey)
        lastStatus = "Local report cleared"
    }
}
