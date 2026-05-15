using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

internal static class Program {
    private const string Begin = "\r\n--ACCOUNTING-WEB-SERVER-URL-BEGIN--\r\n";
    private const string End = "\r\n--ACCOUNTING-WEB-SERVER-URL-END--\r\n";

    [STAThread]
    private static int Main() {
        try {
            string server = ReadServerUrl();
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            ServicePointManager.ServerCertificateValidationCallback = delegate { return true; };
            string tempRoot = Path.Combine(Path.GetTempPath(), "accounting_web_required_setup_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(tempRoot);
            string zipPath = Path.Combine(tempRoot, "payload.zip");
            using (var client = new WebClient()) {
                client.DownloadFile(server.TrimEnd('/') + "/api/setup/user-pc-payload.zip", zipPath);
            }
            ZipFile.ExtractToDirectory(zipPath, tempRoot);
            string setup = Path.Combine(tempRoot, "setup.ps1");
            if (!File.Exists(setup)) setup = Path.Combine(tempRoot, "1_필수프로그램_설치_실행.ps1");
            if (!File.Exists(setup)) throw new FileNotFoundException("setup.ps1 not found", setup);
            string ps = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "System32", "WindowsPowerShell", "v1.0", "powershell.exe");
            var psi = new ProcessStartInfo(ps, "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"" + setup + "\"") {
                UseShellExecute = false,
                CreateNoWindow = true,
                WorkingDirectory = tempRoot,
                WindowStyle = ProcessWindowStyle.Hidden
            };
            Process.Start(psi);
            MessageBox.Show("Accounting WEB setup has started. The tray icon will appear after installation.", "Accounting WEB", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return 0;
        } catch (Exception ex) {
            MessageBox.Show(ex.Message, "Accounting WEB setup failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    private static string ReadServerUrl() {
        string path = Assembly.GetExecutingAssembly().Location;
        string text = Encoding.UTF8.GetString(File.ReadAllBytes(path));
        int begin = text.LastIndexOf(Begin, StringComparison.Ordinal);
        if (begin < 0) return "https://172.17.39.121:8080";
        begin += Begin.Length;
        int end = text.IndexOf(End, begin, StringComparison.Ordinal);
        if (end < 0) return "https://172.17.39.121:8080";
        string value = text.Substring(begin, end - begin).Trim();
        return value.Length == 0 ? "https://172.17.39.121:8080" : value;
    }
}
