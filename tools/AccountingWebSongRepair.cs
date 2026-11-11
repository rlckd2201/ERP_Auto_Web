using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;

internal static class AccountingWebSongRepair {
    private static readonly string[] Resources = { "repair.ps1", "repair-common.ps1", "server105-trust.pem" };
    static int Main(string[] args) {
        try {
            var assembly = Assembly.GetExecutingAssembly();
            if (args.Length == 1 && args[0] == "--self-test") {
                foreach (var name in Resources) {
                    using (var stream = assembly.GetManifestResourceStream(name)) {
                        if (stream == null || stream.Length == 0) return 1;
                    }
                }
                Console.WriteLine("Embedded recovery resources verified. No repair executed.");
                return 0;
            }
            string folder = Path.Combine(Path.GetTempPath(), "AccountingWebSongRepair_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(folder);
            foreach (var name in Resources) {
                using (var source = assembly.GetManifestResourceStream(name))
                using (var target = File.Create(Path.Combine(folder, name))) {
                    if (source == null) throw new InvalidOperationException("Missing recovery resource: " + name);
                    source.CopyTo(target);
                }
            }
            string shell = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "System32", "WindowsPowerShell", "v1.0", "powershell.exe");
            var info = new ProcessStartInfo(shell, "-NoProfile -ExecutionPolicy Bypass -File \"" + Path.Combine(folder, "repair.ps1") + "\"") { UseShellExecute = false };
            using (var process = Process.Start(info)) {
                process.WaitForExit();
                int code = process.ExitCode;
                Console.WriteLine("Press Enter to close this window.");
                Console.ReadLine();
                return code;
            }
        } catch (Exception ex) {
            Console.WriteLine("Recovery could not start: " + ex.Message);
            Console.WriteLine("Press Enter to close this window.");
            Console.ReadLine();
            return 1;
        }
    }
}
