import SwiftUI
import UIKit
import Darwin

@main
struct MadeiraApp: App {
    @Environment(\.scenePhase) private var scenePhase
    var body: some Scene {
        WindowGroup {
            ContentView()
                .modifier(ClaimGamepadEvents())
                .onAppear {
                    StrataForgeSessionLog.start()
                    GamepadInput.shared.start()
                    HardwareInput.shared.start()
                    JITNetworkShortcut.shared.restoreLeftover()   // also starts its network path monitor
                }
                // madeira://jit-network/...: the Madeira JIT shortcut returning (JITNetwork.swift).
                .onOpenURL { url in JITNetworkShortcut.shared.handle(url) }
                .onReceive(NotificationCenter.default.publisher(for: UIApplication.didReceiveMemoryWarningNotification)) { _ in
                    StrataForgeSessionLog.record("memory_warning")
                }
        }
        .onChange(of: scenePhase) { newPhase in
            if newPhase == .background { StrataForgeSessionLog.record("background") }
            if newPhase == .active { StrataForgeSessionLog.record("foreground") }
        }
    }
}

/// Minimal privacy-conscious lifecycle log. No Steam user data, file paths, or URLs.
private enum StrataForgeSessionLog {
    static let maxBytes = 64 * 1024
    static let queue = DispatchQueue(label: "strataforge.lifecycle.log", qos: .utility)
    static var file: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("strataforge-lifecycle.log")
    }
    static func start() { record("launch") }
    static func record(_ event: String) {
        queue.async {
            guard ["launch", "memory_warning", "background", "foreground"].contains(event) else { return }
            let destination = file
            try? FileManager.default.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
            let memory = ProcessInfo.processInfo.physicalMemory
            let entry = "\(Int(Date().timeIntervalSince1970)) event=\(event) device_ram_bytes=\(memory)\\n"
            var existing = (try? Data(contentsOf: destination)) ?? Data()
            if existing.count > maxBytes / 2 { existing = Data(existing.suffix(maxBytes / 2)) }
            existing.append(Data(entry.utf8))
            try? existing.write(to: destination, options: .atomic)
        }
    }
}

