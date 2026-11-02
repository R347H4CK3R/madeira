import SwiftUI
import Metal
import Darwin

@main
struct StrataForgeProbeApp: App {
    var body: some Scene {
        WindowGroup { ProbeHome() }
    }
}
struct ProbeHome: View {
    @State private var report = "Select Run preflight"
    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 18) {
                Label("StrataForge Probe", systemImage: "gamecontroller.fill").font(.title.bold())
                Text("Phase 1: verify host capabilities inside the actual Strata guest. This app does NOT include Wine, FEX, or a Windows game runner.")
                    .foregroundStyle(.secondary)
                Button("Run preflight") { report = preflight() }.buttonStyle(.borderedProminent)
                ScrollView {
                    Text(report).font(.system(.footnote, design: .monospaced))
                        .textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
                }
                ShareLink(item: report) { Label("Export diagnostics", systemImage: "square.and.arrow.up") }
                Spacer()
            }
            .padding()
            .navigationTitle("Runtime preflight")
        }
    }
    func preflight() -> String {
        let device = MTLCreateSystemDefaultDevice()
        let memory = ProcessInfo.processInfo.physicalMemory
        let path = Bundle.main.bundlePath
        var lines = [
            "StrataForge capability preflight",
            "OS: " + ProcessInfo.processInfo.operatingSystemVersionString,
            "CPU family: arm64 (iPhone app target)",
            "Physical RAM reported: " + String(memory / 1024 / 1024) + " MiB",
            "Metal device: " + (device?.name ?? "UNAVAILABLE"),
            "Executable path: " + (Bundle.main.executablePath ?? "unknown"),
            "App bundle: " + path,
            "JIT translated-code execution: NOT TESTED",
            "Wine/FEX translation: NOT INSTALLED",
            "Wine socket handshake: NOT TESTED",
            "Game rendering: NOT TESTED",
            "Strata process/JIT ownership: NOT TESTED",
            "Result: PROBE ONLY — NOT A WORKING EMULATOR"
        ]
        if device == nil { lines.append("BLOCKER: no Metal device") }
        return lines.joined(separator: "\n")
    }
}
