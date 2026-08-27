using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("TWIS Holo Workshop")]
[assembly: AssemblyProduct("TWIS Holo Workshop Desktop Launcher")]
[assembly: AssemblyDescription("Local-only Windows launcher for the TWIS Holo Workshop")]
[assembly: AssemblyCompany("TWIS")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

namespace TwisHoloWorkshopDesktop
{
    internal static class Program
    {
        private const string WorkshopUrl = "http://127.0.0.1:8787/";
        private const string HealthUrl = "http://127.0.0.1:8787/api/health";
        private const int StartupTimeoutMilliseconds = 45000;
        private const int SwRestore = 9;

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern uint SearchPath(string path, string fileName, string extension, int bufferLength, StringBuilder buffer, IntPtr filePart);

        [DllImport("user32.dll")]
        private static extern bool SetForegroundWindow(IntPtr windowHandle);

        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr windowHandle, int command);

        [STAThread]
        private static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            bool ownsMutex = false;
            using (Mutex mutex = new Mutex(true, "Local\\TWISHoloWorkshopDesktopLauncher", out ownsMutex))
            {
                StartupForm startup = new StartupForm();
                startup.Show();
                PumpMessages();

                try
                {
                    if (!ownsMutex)
                    {
                        startup.SetStatus("TWIS is already starting…", "Waiting for the local Workshop service.");
                        WaitForHealth(startup, null, 20000);
                        OpenOrFocusWorkshop();
                        startup.Close();
                        return;
                    }

                    string workshopRoot = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".."));
                    string serverPath = Path.Combine(workshopRoot, "companion", "server.py");
                    if (!Directory.Exists(workshopRoot) || !File.Exists(serverPath))
                    {
                        throw new StartupException(
                            "The Workshop folder could not be found.",
                            "Expected the existing service at: " + serverPath
                        );
                    }

                    string healthDetail;
                    if (!TryGetTwisHealth(out healthDetail))
                    {
                        if (IsPortOpen("127.0.0.1", 8787))
                        {
                            throw new StartupException(
                                "Port 8787 is already in use by something other than TWIS.",
                                "The loopback port accepted a connection, but " + HealthUrl + " did not identify the TWIS local companion. " + healthDetail
                            );
                        }

                        string python = FindOnPath("py.exe");
                        string arguments;
                        if (python != null)
                        {
                            arguments = Quote(serverPath);
                        }
                        else
                        {
                            python = FindOnPath("python.exe");
                            arguments = Quote(serverPath);
                        }

                        if (python == null)
                        {
                            throw new StartupException(
                                "The required Python runtime is missing.",
                                "Neither py.exe nor python.exe could be found on the Windows PATH. TWIS itself was not changed."
                            );
                        }

                        startup.SetStatus("Starting TWIS Holo Workshop…", "Launching the existing local service on this computer.");
                        Process server = StartServer(python, arguments, workshopRoot);
                        WaitForHealth(startup, server, StartupTimeoutMilliseconds);
                    }
                    else
                    {
                        startup.SetStatus("TWIS is already running", "Opening the existing local Workshop.");
                        PumpMessages();
                    }

                    OpenOrFocusWorkshop();
                    startup.Close();
                }
                catch (StartupException error)
                {
                    startup.Close();
                    Application.Run(new FailureForm(error.Message, error.TechnicalDetails));
                }
                catch (Exception error)
                {
                    startup.Close();
                    Application.Run(new FailureForm(
                        "TWIS Holo Workshop could not start.",
                        error.GetType().FullName + ": " + error.Message
                    ));
                }
                finally
                {
                    if (ownsMutex)
                    {
                        mutex.ReleaseMutex();
                    }
                }
            }
        }

        private static Process StartServer(string python, string arguments, string workshopRoot)
        {
            ProcessStartInfo info = new ProcessStartInfo();
            info.FileName = python;
            info.Arguments = arguments;
            info.WorkingDirectory = workshopRoot;
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            info.WindowStyle = ProcessWindowStyle.Hidden;
            info.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"] = "1";
            Process process = Process.Start(info);
            if (process == null)
            {
                throw new StartupException("The local Workshop service failed to start.", "Windows did not return a process for the fixed Python service command.");
            }
            return process;
        }

        private static void WaitForHealth(StartupForm startup, Process process, int timeoutMilliseconds)
        {
            Stopwatch timer = Stopwatch.StartNew();
            string lastDetail = "No health response was received.";
            while (timer.ElapsedMilliseconds < timeoutMilliseconds)
            {
                PumpMessages();
                if (process != null && process.HasExited)
                {
                    throw new StartupException(
                        "The local Workshop service stopped before it became ready.",
                        "The fixed service process exited with code " + process.ExitCode + ". Command: " + process.StartInfo.FileName + " " + process.StartInfo.Arguments
                    );
                }

                if (TryGetTwisHealth(out lastDetail))
                {
                    startup.SetStatus("TWIS is ready", "Opening Sanctuary.");
                    PumpMessages();
                    return;
                }
                Thread.Sleep(250);
            }

            throw new StartupException(
                "TWIS Holo Workshop did not become ready in time.",
                "Health check timed out after " + timeoutMilliseconds + " ms at " + HealthUrl + ". Last result: " + lastDetail
            );
        }

        private static bool TryGetTwisHealth(out string detail)
        {
            try
            {
                HttpWebRequest request = (HttpWebRequest)WebRequest.Create(HealthUrl);
                request.Method = "GET";
                request.Timeout = 1500;
                request.ReadWriteTimeout = 1500;
                request.Proxy = null;
                using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
                using (StreamReader reader = new StreamReader(response.GetResponseStream()))
                {
                    string body = reader.ReadToEnd();
                    bool isTwis = response.StatusCode == HttpStatusCode.OK
                        && Regex.IsMatch(body, "\\\"ok\\\"\\s*:\\s*true", RegexOptions.IgnoreCase)
                        && Regex.IsMatch(body, "\\\"mode\\\"\\s*:\\s*\\\"local-companion\\\"", RegexOptions.IgnoreCase);
                    detail = "HTTP " + (int)response.StatusCode + "; TWIS identity " + (isTwis ? "verified" : "not verified") + ".";
                    return isTwis;
                }
            }
            catch (Exception error)
            {
                detail = error.GetType().Name + ": " + error.Message;
                return false;
            }
        }

        private static bool IsPortOpen(string host, int port)
        {
            try
            {
                using (TcpClient client = new TcpClient())
                {
                    IAsyncResult result = client.BeginConnect(host, port, null, null);
                    bool connected = result.AsyncWaitHandle.WaitOne(500);
                    if (connected)
                    {
                        client.EndConnect(result);
                    }
                    return connected;
                }
            }
            catch
            {
                return false;
            }
        }

        private static void OpenOrFocusWorkshop()
        {
            foreach (Process process in Process.GetProcessesByName("msedge"))
            {
                try
                {
                    if (process.MainWindowHandle != IntPtr.Zero && process.MainWindowTitle.IndexOf("Twis Holo Workshop", StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        ShowWindow(process.MainWindowHandle, SwRestore);
                        SetForegroundWindow(process.MainWindowHandle);
                        return;
                    }
                }
                catch
                {
                    // A short-lived Edge helper process may disappear during enumeration.
                }
            }

            string edge = FindEdge();
            if (edge == null)
            {
                throw new StartupException(
                    "Microsoft Edge could not be found.",
                    "The Workshop service is healthy, but the Windows Edge application executable was not found in either standard Program Files location."
                );
            }

            ProcessStartInfo info = new ProcessStartInfo();
            info.FileName = edge;
            string profile = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "TWIS Holo Workshop",
                "EdgeProfile"
            );
            Directory.CreateDirectory(profile);
            info.Arguments = "--app=" + WorkshopUrl
                + " --user-data-dir=" + Quote(profile)
                + " --new-window --no-first-run --no-default-browser-check"
                + " --disable-background-networking --disable-component-update --disable-sync --metrics-recording-only";
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            info.WindowStyle = ProcessWindowStyle.Normal;
            Process.Start(info);
        }

        private static string FindEdge()
        {
            string x86 = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);
            string x64 = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
            string[] candidates = new string[]
            {
                Path.Combine(x86, "Microsoft", "Edge", "Application", "msedge.exe"),
                Path.Combine(x64, "Microsoft", "Edge", "Application", "msedge.exe")
            };
            foreach (string candidate in candidates)
            {
                if (File.Exists(candidate)) return candidate;
            }
            return null;
        }

        private static string FindOnPath(string executable)
        {
            StringBuilder buffer = new StringBuilder(32768);
            uint length = SearchPath(null, executable, null, buffer.Capacity, buffer, IntPtr.Zero);
            if (length > 0 && length < buffer.Capacity && File.Exists(buffer.ToString()))
            {
                return buffer.ToString();
            }
            return null;
        }

        private static string Quote(string value)
        {
            return "\"" + value.Replace("\"", "\\\"") + "\"";
        }

        private static void PumpMessages()
        {
            Application.DoEvents();
        }
    }

    internal sealed class StartupException : Exception
    {
        public string TechnicalDetails { get; private set; }

        public StartupException(string message, string technicalDetails) : base(message)
        {
            TechnicalDetails = technicalDetails;
        }
    }

    internal sealed class StartupForm : Form
    {
        private readonly Label title;
        private readonly Label status;

        public StartupForm()
        {
            Text = "TWIS Holo Workshop";
            ClientSize = new Size(520, 230);
            MinimumSize = new Size(520, 230);
            MaximumSize = new Size(520, 230);
            StartPosition = FormStartPosition.CenterScreen;
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            BackColor = Color.FromArgb(7, 16, 25);
            ForeColor = Color.FromArgb(225, 249, 252);

            Panel rail = new Panel();
            rail.BackColor = Color.FromArgb(30, 220, 239);
            rail.Location = new Point(0, 0);
            rail.Size = new Size(8, 230);
            Controls.Add(rail);

            Label eyebrow = MakeLabel("LOCAL WORKSHOP · DESKTOP ENTRY", 29, 27, 450, 24, 9, FontStyle.Bold, Color.FromArgb(196, 151, 79));
            title = MakeLabel("Starting TWIS Holo Workshop…", 29, 65, 450, 42, 18, FontStyle.Bold, Color.FromArgb(225, 249, 252));
            status = MakeLabel("Checking the local Workshop service.", 31, 119, 430, 54, 10, FontStyle.Regular, Color.FromArgb(139, 198, 207));
            Controls.Add(eyebrow);
            Controls.Add(title);
            Controls.Add(status);

            Label local = MakeLabel("LOCAL ONLY  ·  127.0.0.1", 31, 189, 430, 22, 8, FontStyle.Bold, Color.FromArgb(73, 139, 150));
            Controls.Add(local);
        }

        public void SetStatus(string heading, string detail)
        {
            title.Text = heading;
            status.Text = detail;
            Refresh();
        }

        private Label MakeLabel(string text, int x, int y, int width, int height, float size, FontStyle style, Color color)
        {
            Label label = new Label();
            label.Text = text;
            label.Location = new Point(x, y);
            label.Size = new Size(width, height);
            label.Font = new Font("Segoe UI", size, style);
            label.ForeColor = color;
            label.BackColor = Color.Transparent;
            return label;
        }
    }

    internal sealed class FailureForm : Form
    {
        private readonly TextBox details;
        private readonly Button detailsButton;

        public FailureForm(string message, string technicalDetails)
        {
            Text = "TWIS Holo Workshop — Startup problem";
            ClientSize = new Size(610, 315);
            MinimumSize = new Size(610, 315);
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.FromArgb(15, 17, 22);
            ForeColor = Color.FromArgb(240, 240, 240);

            Label heading = MakeLabel("TWIS Holo Workshop could not start.", 28, 24, 540, 36, 16, FontStyle.Bold, Color.FromArgb(255, 220, 205));
            Label body = MakeLabel(message, 30, 74, 530, 58, 10, FontStyle.Regular, Color.FromArgb(220, 225, 228));
            Label safe = MakeLabel("Your Workshop files and database were not changed.", 30, 139, 530, 28, 9, FontStyle.Bold, Color.FromArgb(103, 226, 239));
            Controls.Add(heading);
            Controls.Add(body);
            Controls.Add(safe);

            detailsButton = new Button();
            detailsButton.Text = "Show technical details";
            detailsButton.Location = new Point(30, 183);
            detailsButton.Size = new Size(170, 34);
            detailsButton.FlatStyle = FlatStyle.Flat;
            detailsButton.ForeColor = Color.FromArgb(103, 226, 239);
            detailsButton.FlatAppearance.BorderColor = Color.FromArgb(52, 139, 150);
            detailsButton.Click += ToggleDetails;
            Controls.Add(detailsButton);

            Button close = new Button();
            close.Text = "Close";
            close.Location = new Point(460, 183);
            close.Size = new Size(100, 34);
            close.FlatStyle = FlatStyle.Flat;
            close.ForeColor = Color.FromArgb(235, 235, 235);
            close.DialogResult = DialogResult.OK;
            Controls.Add(close);
            AcceptButton = close;

            details = new TextBox();
            details.Text = technicalDetails;
            details.Location = new Point(30, 235);
            details.Size = new Size(530, 130);
            details.Multiline = true;
            details.ReadOnly = true;
            details.ScrollBars = ScrollBars.Vertical;
            details.BackColor = Color.FromArgb(5, 10, 15);
            details.ForeColor = Color.FromArgb(185, 220, 225);
            details.Font = new Font("Consolas", 8.5f);
            details.Visible = false;
            Controls.Add(details);
        }

        private void ToggleDetails(object sender, EventArgs eventArgs)
        {
            details.Visible = !details.Visible;
            ClientSize = new Size(610, details.Visible ? 395 : 315);
            detailsButton.Text = details.Visible ? "Hide technical details" : "Show technical details";
        }

        private Label MakeLabel(string text, int x, int y, int width, int height, float size, FontStyle style, Color color)
        {
            Label label = new Label();
            label.Text = text;
            label.Location = new Point(x, y);
            label.Size = new Size(width, height);
            label.Font = new Font("Segoe UI", size, style);
            label.ForeColor = color;
            label.BackColor = Color.Transparent;
            return label;
        }
    }
}
