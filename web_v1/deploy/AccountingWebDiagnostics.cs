using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Management;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Text;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using Microsoft.Win32;

// Read-only diagnostics: no installer, registry writes, uploads, or credential reads.
internal static class AccountingWebDiagnostics {
    static readonly string[] Modules = { "pyautogui", "pyperclip", "pywinauto", "psutil", "win32gui", "win32con", "win32print", "fitz", "PIL", "requests" };
    static readonly List<string> Roots = new List<string>();
    static readonly List<string> Pythons = new List<string>();
    static string SafeUrl(string value) {
        Uri uri;
        if (!Uri.TryCreate(value, UriKind.Absolute, out uri) || (uri.Scheme != "https" && uri.Scheme != "http")) return "invalid_or_absent";
        var safe = new UriBuilder(uri) { UserName = "", Password = "", Query = "", Fragment = "" };
        return safe.Uri.GetLeftPart(UriPartial.Path);
    }
    static string ServerFromText(string text) {
        Match m = Regex.Match(text ?? "", @"https?://[^\s'""<>]+", RegexOptions.IgnoreCase);
        return m.Success ? SafeUrl(m.Value) : "not_found";
    }
    static object Attempt(Func<object> action) {
        try { return action(); }
        catch (Exception e) { return new { error_type = e.GetType().Name }; }
    }
    static void AddUnique(List<string> list, string path) {
        if (!String.IsNullOrWhiteSpace(path) && !list.Contains(path, StringComparer.OrdinalIgnoreCase)) list.Add(path);
    }
    static object Tcp(string host, int port) {
        using (var client = new TcpClient()) {
            var timer = Stopwatch.StartNew();
            try {
                var pending = client.BeginConnect(host, port, null, null);
                if (!pending.AsyncWaitHandle.WaitOne(3000)) return new { host, port, result = "timeout", elapsed_ms = timer.ElapsedMilliseconds };
                client.EndConnect(pending);
                return new { host, port, result = "connected", elapsed_ms = timer.ElapsedMilliseconds };
            } catch (SocketException e) { return new { host, port, result = e.SocketErrorCode.ToString(), elapsed_ms = timer.ElapsedMilliseconds }; }
        }
    }
    static object Http(string url) {
        var request = (HttpWebRequest)WebRequest.Create(url);
        request.Method = "GET";
        request.AllowAutoRedirect = false;
        request.Timeout = 5000;
        request.ReadWriteTimeout = 5000;
        request.UserAgent = "AccountingWeb-Diagnostics/1.0";
        try { using (var response = (HttpWebResponse)request.GetResponse()) return HttpSummary(url, response); }
        catch (WebException e) {
            var response = e.Response as HttpWebResponse;
            if (response != null) { using (response) return HttpSummary(url, response); }
            return new { url = SafeUrl(url), result = e.Status.ToString(), error_type = e.GetType().Name };
        }
    }
    static object HttpSummary(string url, HttpWebResponse response) {
        // Never include response bodies, cookies, authentication headers or query strings.
        return new { url = SafeUrl(url), status = (int)response.StatusCode, content_type = response.ContentType,
            redirect_path = SafeUrl(response.Headers["Location"] ?? "") };
    }
    static object Protocol() {
        using (var key = Registry.CurrentUser.OpenSubKey(@"Software\Classes\accountingweb\shell\open\command")) {
            string command = key == null ? "" : Convert.ToString(key.GetValue(""));
            Match match = Regex.Match(command, @"-File\s+""([^""]+\.ps1)""", RegexOptions.IgnoreCase);
            string launcher = match.Success ? Environment.ExpandEnvironmentVariables(match.Groups[1].Value) : "";
            bool exists = File.Exists(launcher);
            if (exists) AddUnique(Roots, Path.GetDirectoryName(launcher));
            string server = exists ? ServerFromText(File.ReadAllText(launcher)) : "not_found";
            using (var run = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run"))
                return new { registered = !String.IsNullOrEmpty(command), launcher_path = launcher, launcher_exists = exists,
                    configured_server = server, startup_registered = run != null && run.GetValue("AccountingWebAgent") != null };
        }
    }
    static object AgentProcesses() {
        var output = new List<object>();
        var options = new EnumerationOptions { Timeout = TimeSpan.FromSeconds(8), ReturnImmediately = false };
        using (var searcher = new ManagementObjectSearcher(new ManagementScope(), new ObjectQuery(
            "SELECT ProcessId,Name,CommandLine FROM Win32_Process WHERE Name='python.exe' OR Name='pythonw.exe'"), options)) {
            foreach (ManagementObject process in searcher.Get()) {
                string command = Convert.ToString(process["CommandLine"]);
                if (command.IndexOf("erp_agent.py", StringComparison.OrdinalIgnoreCase) >= 0)
                    output.Add(new { pid = process["ProcessId"], executable = process["Name"], server = ServerFromText(command) });
            }
        }
        return output;
    }
    static void PythonRegistry(RegistryKey hive) {
        using (var core = hive.OpenSubKey(@"Software\Python\PythonCore")) {
            if (core == null) return;
            foreach (string version in core.GetSubKeyNames()) {
                using (var install = core.OpenSubKey(version + @"\InstallPath")) {
                    if (install == null) continue;
                    string executable = Convert.ToString(install.GetValue("ExecutablePath"));
                    if (String.IsNullOrEmpty(executable)) executable = Path.Combine(Convert.ToString(install.GetValue("")), "python.exe");
                    AddUnique(Pythons, executable);
                }
            }
        }
    }
    static object PythonInfo(string executable) {
        string site = Path.Combine(Path.GetDirectoryName(executable), "Lib", "site-packages");
        var found = new Dictionary<string, bool>();
        foreach (string module in Modules) {
            string binary = module == "win32gui" || module == "win32con" || module == "win32print" ? "win32" : module;
            found[module] = Directory.Exists(Path.Combine(site, binary)) || File.Exists(Path.Combine(site, module + ".py")) || File.Exists(Path.Combine(site, module + ".pyd"));
        }
        return new { path = executable, version = FileVersionInfo.GetVersionInfo(executable).ProductVersion, module_files_present = found,
            note = "File presence only; modules are not imported and no Python code is executed." };
    }
    static object InstallInfo(string root) {
        string versionFile = Path.Combine(root, @"web_v1\VERSION");
        string value = File.Exists(versionFile) ? File.ReadAllText(versionFile).Trim() : "missing";
        if (!Regex.IsMatch(value, @"^[0-9A-Za-z._-]{1,50}$")) value = "unrecognized";
        string launcher = Path.Combine(root, "담당자PC_필수프로그램_실행.ps1");
        return new { root, exists = Directory.Exists(root), version = value,
            agent_exists = File.Exists(Path.Combine(root, @"web_v1\agent\erp_agent.py")),
            requirements_exists = File.Exists(Path.Combine(root, @"web_v1\backend\requirements.txt")),
            launcher_exists = File.Exists(launcher), configured_server = File.Exists(launcher) ? ServerFromText(File.ReadAllText(launcher)) : "not_found",
            config_exists = File.Exists(Path.Combine(root, @"support\config.ini")) };
    }
    static object AgentLog() {
        string file = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), @"AccountingWeb\agent.log");
        if (!File.Exists(file)) return new { exists = false, path = file };
        string text;
        using (var stream = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.ReadWrite)) {
            stream.Seek(Math.Max(0, stream.Length - 65536), SeekOrigin.Begin);
            using (var reader = new StreamReader(stream, Encoding.UTF8)) text = reader.ReadToEnd();
        }
        var categories = new Dictionary<string, int>();
        foreach (string marker in new[] { "heartbeat failed", "ConnectionError", "ConnectTimeout", "ReadTimeout", "SSLError", "CERTIFICATE_VERIFY_FAILED", "ModuleNotFoundError", "PermissionError", "package repair failed", "Traceback", "403", "502" })
            categories[marker] = Regex.Matches(text, Regex.Escape(marker), RegexOptions.IgnoreCase).Count;
        return new { exists = true, path = file, last_write = File.GetLastWriteTime(file).ToString("o"), recent_error_categories = categories,
            note = "Only classified error counts from the last64KB; raw logs and business contents are excluded." };
    }
    static object RecentSetup() {
        return Directory.GetDirectories(Path.GetTempPath(), "accounting_web_required_setup_*")
            .OrderByDescending(Directory.GetLastWriteTime).Take(4)
            .Select(dir => new { folder = Path.GetFileName(dir), last_write = Directory.GetLastWriteTime(dir).ToString("o"),
                payload_downloaded = File.Exists(Path.Combine(dir, "payload.zip")), setup_extracted = File.Exists(Path.Combine(dir, "setup.ps1")) }).ToArray();
    }
    static int Main(string[] args) {
        if (args.Contains("--self-test")) {
            if (SafeUrl("https://user:password@example.com/path?token=secret#fragment") != "https://example.com/path" || ServerFromText("--server \"https://172.16.19.105:3010\"") != "https://172.16.19.105:3010/") return 1;
            Console.WriteLine("URL redaction and configured-server parsing passed."); return 0;
        }
        try {
            Console.OutputEncoding = Encoding.UTF8;
            Console.WriteLine("회계업무 진단 중입니다. 약 30초 정도 기다려 주세요.");
            Console.WriteLine("설정 변경·설치·업로드를 하지 않으며 비밀번호와 업무 문서는 수집하지 않습니다.");
            var report = new Dictionary<string, object>();
            report["created_at"] = DateTimeOffset.Now.ToString("o");
            report["computer"] = Environment.MachineName;
            report["windows_user"] = Environment.UserName;
            report["os"] = Environment.OSVersion.ToString();
            report["ipv4"] = Attempt(() => NetworkInterface.GetAllNetworkInterfaces().Where(n => n.OperationalStatus == OperationalStatus.Up)
                .SelectMany(n => n.GetIPProperties().UnicastAddresses).Where(a => a.Address.AddressFamily == AddressFamily.InterNetwork)
                .Select(a => a.Address.ToString()).ToArray());
            AddUnique(Roots, Environment.GetEnvironmentVariable("ACCOUNTING_WEB_INSTALL_ROOT"));
            AddUnique(Roots, Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), @"개발파일\회계업무 자동화_WEB_Version"));
            AddUnique(Roots, Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), @"Desktop\개발파일\회계업무 자동화_WEB_Version"));
            report["protocol"] = Attempt(Protocol);
            report["installations"] = Roots.Select(root => Attempt(() => InstallInfo(root))).ToArray();
            report["agent_processes"] = Attempt(AgentProcesses);
            report["agent_log"] = Attempt(AgentLog);
            report["recent_setup"] = Attempt(RecentSetup);
            Attempt(() => { PythonRegistry(Registry.CurrentUser); PythonRegistry(Registry.LocalMachine); return true; });
            string pythonRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Python");
            if (Directory.Exists(pythonRoot)) foreach (string dir in Directory.GetDirectories(pythonRoot)) AddUnique(Pythons, Path.Combine(dir, "python.exe"));
            report["python"] = Pythons.Where(File.Exists).Select(exe => Attempt(() => PythonInfo(exe))).ToArray();
            report["certificate_file_exists"] = File.Exists(@"C:\ERP_DB\certs\web_v1.cert.pem");
            report["tcp_3010"] = Attempt(() => Tcp("172.16.19.105", 3010));
            report["tcp_portal"] = Attempt(() => Tcp("portal.dae-seung.co.kr", 443));
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            report["agent_version_endpoint"] = Attempt(() => Http("https://172.16.19.105:3010/api/version"));
            report["agent_certificate_endpoint"] = Attempt(() => Http("https://172.16.19.105:3010/api/setup/certificate"));
            report["portal_endpoint"] = Attempt(() => Http("https://portal.dae-seung.co.kr/accounting-automation/"));
            string output = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
            int index = Array.IndexOf(args, "--output");
            if (index >= 0 && index + 1 < args.Length) output = Path.GetFullPath(args[index + 1]);
            Directory.CreateDirectory(output);
            string result = Path.Combine(output, "AccountingWeb_Diagnostics_" + Environment.MachineName + "_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".json");
            File.WriteAllText(result, new JavaScriptSerializer().Serialize(report), new UTF8Encoding(false));
            Console.WriteLine("진단 완료. 다음 결과 파일을 김기창 매니저에게 전달해 주세요:");
            Console.WriteLine(result);
            if (!args.Contains("--no-pause")) { Console.WriteLine("Enter를 누르면 닫힙니다."); Console.ReadLine(); }
            return 0;
        } catch (Exception e) { Console.WriteLine("진단 실패: " + e.GetType().Name); if (!args.Contains("--no-pause")) Console.ReadLine(); return 1; }
    }
}
