import Foundation
import SwiftUI

/// Crash-suspect and runtime error journal. No personal data or raw game logs.
final class StrataForgeCrashReporter: ObservableObject {
    static let shared = StrataForgeCrashReporter()
    @Published var enabled = UserDefaults.standard.bool(forKey: "sf.reports.enabled") {
        didSet { UserDefaults.standard.set(enabled, forKey: "sf.reports.enabled") }
    }
    @Published private(set) var lastStatus = "Reports saved locally"
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
