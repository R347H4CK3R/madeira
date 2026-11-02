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
                .onChange(of: scenePhase) { newPhase in
                    if newPhase == .background { StrataForgeSessionLog.record("background") }
                    if newPhase == .active { StrataForgeSessionLog.record("foreground") }
                }
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
    private static func residentBytes() -> UInt64 {
        var info = mach_task_basic_info_data_t()
        var count = mach_msg_type_number_t(MemoryLayout<mach_task_basic_info_data_t>.size / MemoryLayout<natural_t>.size)
        let status = withUnsafeMutablePointer(to: &info) { ptr in
            ptr.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                task_info(mach_task_self_, task_flavor_t(MACH_TASK_BASIC_INFO), $0, &count)
            }
        }
        return status == KERN_SUCCESS ? UInt64(info.resident_size) : 0
    }

    static func record(_ event: String) {
        queue.async {
            guard ["launch", "memory_warning", "background", "foreground"].contains(event) else { return }
            let destination = file
            try? FileManager.default.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
            let memory = residentBytes()
            let entry = "\(Int(Date().timeIntervalSince1970)) event=\(event) resident_bytes=\(memory)\\n"
            var existing = (try? Data(contentsOf: destination)) ?? Data()
            if existing.count > maxBytes / 2 { existing = Data(existing.suffix(maxBytes / 2)) }
            existing.append(Data(entry.utf8))
            try? existing.write(to: destination, options: .atomic)
        }
    }
}

