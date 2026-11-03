import Foundation
import Darwin

/// StrataForge bounded diagnostic recorder. Integrate this with the actual Wine/FEX
/// launcher after the missing native runtime builds; it makes no JIT/gameplay claims.
enum StrataForgeDiagnostics {
    static let maximumLogBytes = 128 * 1024
    static let directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        .appendingPathComponent("StrataForgeDiagnostics", isDirectory: true)
    static let logURL = directory.appendingPathComponent("latest.log")
    static let pendingURL = directory.appendingPathComponent("previous-session.log")
    private static let queue = DispatchQueue(label: "strataforge.diagnostics", qos: .utility)

    static func beginSession() {
        queue.async {
            let fm = FileManager.default
            try? fm.createDirectory(at: directory, withIntermediateDirectories: true)
            if fm.fileExists(atPath: logURL.path) {
                try? fm.removeItem(at: pendingURL)
                try? fm.moveItem(at: logURL, to: pendingURL)
            }
            write("session_start os=\(ProcessInfo.processInfo.operatingSystemVersionString)")
        }
    }
    static func event(_ name: String, details: String = "") {
        queue.async { write("\(clean(name)) \(clean(details)) rss_bytes=\(residentBytes())") }
    }
    static func markNormalExit() {
        event("session_normal_exit")
        // Previous-session reports are retained for user inspection; no automatic
        // credential-bearing upload is performed on application startup.
    }
    static func previousLogForReview() -> URL? {
        FileManager.default.fileExists(atPath: pendingURL.path) ? pendingURL : nil
    }
    private static func clean(_ value: String) -> String {
        var text = String(value.prefix(1024))
        // Avoid including user-provided paths, credentials or arbitrary logs.
        if text.contains("://") || text.contains("@") || text.localizedCaseInsensitiveContains("token")
            || text.localizedCaseInsensitiveContains("password") {
            text = "[sensitive details omitted]"
        }
        return text.replacingOccurrences(of: "\n", with: " ")
    }
    private static func write(_ line: String) {
        let fm = FileManager.default
        let bytes = Data(("\(Date().timeIntervalSince1970) \(line)\n").utf8)
        if !fm.fileExists(atPath: logURL.path) { fm.createFile(atPath: logURL.path, contents: Data()) }
        guard let handle = try? FileHandle(forWritingTo: logURL) else { return }
        defer { try? handle.close() }
        let oldSize = (try? handle.seekToEnd()) ?? 0
        if oldSize + UInt64(bytes.count) > UInt64(maximumLogBytes) {
            try? handle.close()
            let keep = (try? Data(contentsOf: logURL).suffix(maximumLogBytes / 2)) ?? Data()
            try? Data(keep).write(to: logURL, options: .atomic)
            guard let next = try? FileHandle(forWritingTo: logURL) else { return }
            defer { try? next.close() }
            _ = try? next.seekToEnd()
            try? next.write(contentsOf: bytes)
        } else {
            try? handle.write(contentsOf: bytes)
        }
    }
    private static func residentBytes() -> UInt64 {
        var info = mach_task_basic_info_data_t()
        var count = mach_msg_type_number_t(MemoryLayout<mach_task_basic_info_data_t>.size / MemoryLayout<natural_t>.size)
        let result = withUnsafeMutablePointer(to: &info) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                task_info(mach_task_self_, task_flavor_t(MACH_TASK_BASIC_INFO), $0, &count)
            }
        }
        return result == KERN_SUCCESS ? UInt64(info.resident_size) : 0
    }
}
