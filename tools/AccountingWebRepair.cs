using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;

internal static class AccountingWebRepair {
    static int Main(string[] args) {
        try {
            string script;
            using (var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("repair.ps1"))
            using (var reader = new StreamReader(stream, Encoding.UTF8)) script = reader.ReadToEnd();
            if (args.Length == 1 && args[0] == "--self-test") {
                if (!script.Contains("Get-PythonProbe") || !script.Contains("agent_started_server_heartbeat_pending") || !script.Contains("현시훈PC")) return 1;
                Console.WriteLine("Embedded repair resource verified; no repair executed.");
                return 0;
            }
            string folder = Path.Combine(Path.GetTempPath(), "AccountingWebRepair_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(folder);
            string path = Path.Combine(folder, "repair.ps1");
            File.WriteAllText(path, script, new UTF8Encoding(true));
            string shell = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "System32", "WindowsPowerShell", "v1.0", "powershell.exe");
            var info = new ProcessStartInfo(shell, "-NoProfile -ExecutionPolicy Bypass -File \"" + path + "\"") { UseShellExecute = false };
            using (var process = Process.Start(info)) {
                process.WaitForExit();
                int code = process.ExitCode;
                Console.WriteLine("Press Enter to close this window.");
                Console.ReadLine();
                return code;
            }
        } catch (Exception ex) {
            Console.WriteLine("Repair could not start: " + ex.Message);
            Console.WriteLine("Press Enter to close this window.");
            Console.ReadLine();
            return 1;
        }
    }
}
