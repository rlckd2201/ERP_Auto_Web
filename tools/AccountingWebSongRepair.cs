using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Web.Script.Serialization;

internal static class AccountingWebSongRepair {
    private static readonly string[] Resources = { "repair.ps1", "repair-common.ps1", "server105-trust.pem" };
    private static readonly object LogLock = new object();
    private static readonly JavaScriptSerializer Json = new JavaScriptSerializer();
    private static readonly Encoding Utf8 = new UTF8Encoding(true);
    private static string ResultPath;
    private static string LogPath;

    private static void Save(IDictionary<string, object> report) {
        report["launcher_version"] = 2;
        report["result_file"] = ResultPath;
        report["log_file"] = LogPath;
        File.WriteAllText(ResultPath, Json.Serialize(report), Utf8);
    }

    private static void Log(string line) {
        if (line == null) return;
        lock (LogLock) {
            Console.WriteLine(line);
            if (LogPath != null) {
                try { File.AppendAllText(LogPath, line + Environment.NewLine, Encoding.UTF8); }
                catch (IOException) { Console.WriteLine("The text log could not be updated."); }
                catch (UnauthorizedAccessException) { Console.WriteLine("Text log access was denied."); }
            }
        }
    }

    private static void PrepareResult(List<string> folders, IDictionary<string, object> report) {
        if (folders.Count == 0) {
            folders.Add(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory));
            folders.Add(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location));
            folders.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AccountingWeb", "RepairResults"));
            folders.Add(Path.Combine(Path.GetTempPath(), "AccountingWebRepairResults"));
        }
        string stem = "AccountingWeb_SongRepair_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + "_" + Guid.NewGuid().ToString("N").Substring(0, 8);
        var failures = new List<string>();
        foreach (string folder in folders) {
            try {
                if (String.IsNullOrWhiteSpace(folder)) continue;
                string full = Path.GetFullPath(folder);
                Directory.CreateDirectory(full);
                ResultPath = Path.Combine(full, stem + ".json");
                LogPath = Path.Combine(full, stem + ".log");
                using (new FileStream(ResultPath, FileMode.CreateNew, FileAccess.Write)) { }
                using (new FileStream(LogPath, FileMode.CreateNew, FileAccess.Write)) { }
                report["output_fallback_errors"] = failures.ToArray();
                Save(report);
                return;
            } catch (Exception ex) {
                failures.Add(folder + ": " + ex.Message);
                ResultPath = null;
                LogPath = null;
            }
        }
        throw new IOException("No writable result folder: " + String.Join("; ", failures.ToArray()));
    }

    static int Main(string[] args) {
        Console.OutputEncoding = Encoding.UTF8;
        bool noPause = false;
        int code = 1;
        var report = new Dictionary<string, object> {
            { "status", "launcher_started" }, { "created_at", DateTime.Now.ToString("o") },
            { "computer", Environment.MachineName }, { "user", Environment.UserName }
        };
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
            var folders = new List<string>();
            for (int i = 0; i < args.Length; i++) {
                if (args[i] == "--no-pause") noPause = true;
                else if (args[i] == "--output-dir" && i + 1 < args.Length) folders.Add(args[++i]);
                else throw new ArgumentException("Unknown or incomplete recovery option.");
            }
            PrepareResult(folders, report);
            Log("Accounting WEB Song recovery v2");
            Log("결과 JSON: " + ResultPath);
            Log("실행 로그: " + LogPath);
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
            // Set encoding before parsing the child file, so startup errors and
            // Korean paths remain readable even if the child cannot execute.
            string command = "[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false); $OutputEncoding = [Console]::OutputEncoding; $ProgressPreference = 'SilentlyContinue'; & '"
                + Path.Combine(folder, "repair.ps1").Replace("'", "''") + "' -ResultPath '"
                + ResultPath.Replace("'", "''") + "'; exit $LASTEXITCODE";
            string arguments = "-NoProfile -ExecutionPolicy Bypass -OutputFormat Text -EncodedCommand "
                + Convert.ToBase64String(Encoding.Unicode.GetBytes(command));
            var info = new ProcessStartInfo(shell, arguments) {
                UseShellExecute = false, CreateNoWindow = true,
                RedirectStandardOutput = true, RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8
            };
            using (var process = new Process { StartInfo = info }) {
                process.OutputDataReceived += (sender, item) => Log(item.Data);
                process.ErrorDataReceived += (sender, item) => Log(item.Data);
                process.Start();
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();
                process.WaitForExit();
                code = process.ExitCode;
            }
            var child = Json.DeserializeObject(File.ReadAllText(ResultPath, Encoding.UTF8)) as Dictionary<string, object>;
            if (child == null || !child.ContainsKey("repair_version") || Convert.ToInt32(child["repair_version"]) != 2
                    || !child.ContainsKey("completed_at")) {
                report["status"] = "needs_support";
                report["error"] = "PowerShell ended before completing its report. Check the adjacent execution log.";
                report["powershell_exit_code"] = code;
                code = code == 0 ? 1 : code;
            } else {
                child["output_fallback_errors"] = report["output_fallback_errors"];
                report = child;
                report["powershell_exit_code"] = code;
                if (code != 0) report["status"] = "needs_support";
            }
            report["launcher_completed_at"] = DateTime.Now.ToString("o");
            Save(report);
        } catch (Exception ex) {
            code = 1;
            report["status"] = "needs_support";
            report["launcher_error"] = ex.Message;
            report["launcher_completed_at"] = DateTime.Now.ToString("o");
            Log("Recovery could not finish: " + ex.Message);
            if (ResultPath != null) {
                try { Save(report); }
                catch (Exception saveError) { Console.WriteLine("Result save failed: " + saveError.Message); }
            }
        }
        if (ResultPath != null) {
            Log("결과 JSON: " + ResultPath);
            Log("실행 로그: " + LogPath);
        }
        if (!noPause) {
            if (ResultPath != null && File.Exists(ResultPath)) {
                try { Process.Start(new ProcessStartInfo("explorer.exe", "/select,\"" + ResultPath + "\"") { UseShellExecute = true }); }
                catch (Exception ex) { Log("결과 폴더를 열지 못했습니다: " + ex.Message); }
            }
            Console.WriteLine("Press Enter to close this window.");
            Console.ReadLine();
        }
        return code;
    }
}
