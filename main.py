import sys
import re
from PyQt5.QtCore import QUrl, Qt, QSize
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QLabel, QMessageBox, QListWidgetItem,
    QDialog, QGridLayout, QFrame
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
import threading
import time
from collections import defaultdict, Counter
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

# ------------------------------ Firewall Web Engine Page ------------------------------ #

class FirewallWebEnginePage(QWebEnginePage):
    """
    Custom QWebEnginePage that overrides the navigation request to implement firewall filtering.
    """
    def __init__(self, blocked_sites, parent=None):
        super().__init__(parent)
        self.blocked_sites = blocked_sites

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        """
        Intercept navigation requests and block if the URL is in the blocked_sites list.
        """
        if _type == QWebEnginePage.NavigationTypeLinkClicked or _type == QWebEnginePage.NavigationTypeTyped:
            domain = url.host().lower()
            for site in self.blocked_sites:
                if domain == site.lower() or domain.endswith('.' + site.lower()):
                    # Log the blocked attempt
                    parent_window = self.parent()
                    if isinstance(parent_window, MainWindow):
                        parent_window.log_blocked_attempt(url.toString())
                    # Show blocked page
                    self.parent().show_blocked_page(url.toString())
                    return False
        return super().acceptNavigationRequest(url, _type, isMainFrame)

# ------------------------------ Status Dialog ------------------------------ #

class StatusDialog(QDialog):
    """
    Dialog to display all blocked website access attempts.
    """
    def __init__(self, blocked_attempts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Firewall Status")
        self.setGeometry(150, 150, 600, 400)
        self.blocked_attempts = blocked_attempts
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Total blocked attempts
        total_blocked = len(self.blocked_attempts)
        total_label = QLabel(f"Total Blocked Attempts: {total_blocked}")
        total_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(total_label)

        # List of blocked URLs
        list_label = QLabel("Blocked Websites Accessed:")
        list_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(list_label)

        blocked_list = QListWidget()
        for attempt in self.blocked_attempts:
            blocked_list.addItem(attempt)
        layout.addWidget(blocked_list)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

# ------------------------------ Statistics Dialog ------------------------------ #

class StatisticsDialog(QDialog):
    """
    Dialog to display detailed statistics about blocked attempts.
    """
    def __init__(self, blocked_attempts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Firewall Statistics")
        self.setGeometry(200, 200, 800, 600)
        self.blocked_attempts = blocked_attempts
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Total blocked attempts
        total_blocked = len(self.blocked_attempts)
        total_label = QLabel(f"Total Blocked Attempts: {total_blocked}")
        total_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(total_label)

        # Top blocked sites
        top_sites = self.get_top_blocked_sites()
        top_sites_label = QLabel("Top Blocked Sites:")
        top_sites_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(top_sites_label)

        top_sites_list = QListWidget()
        for site, count in top_sites:
            top_sites_list.addItem(f"{site} - {count} times")
        layout.addWidget(top_sites_list)

        # Blocked attempts over time
        time_graph_label = QLabel("Blocked Attempts Over Time:")
        time_graph_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(time_graph_label)

        # Create a matplotlib figure for the time graph
        self.time_fig, self.time_ax = plt.subplots(figsize=(8, 3))
        self.time_canvas = FigureCanvas(self.time_fig)
        layout.addWidget(self.time_canvas)
        self.plot_blocked_over_time()

        # Top blocked sites graph
        sites_graph_label = QLabel("Top Blocked Sites Graph:")
        sites_graph_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(sites_graph_label)

        self.sites_fig, self.sites_ax = plt.subplots(figsize=(6, 4))
        self.sites_canvas = FigureCanvas(self.sites_fig)
        layout.addWidget(self.sites_canvas)
        self.plot_top_sites_graph()

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

    def get_top_blocked_sites(self):
        """
        Returns the top 5 blocked sites based on access attempts.
        """
        sites = [attempt.split(" - ")[-1] for attempt in self.blocked_attempts]
        site_counts = Counter(sites)
        return site_counts.most_common(5)

    def plot_blocked_over_time(self):
        """
        Plots blocked attempts over time.
        """
        if not self.blocked_attempts:
            self.time_ax.text(0.5, 0.5, 'No data available', horizontalalignment='center',
                              verticalalignment='center', transform=self.time_ax.transAxes)
            self.time_canvas.draw()
            return

        # Extract timestamps
        timestamps = []
        for attempt in self.blocked_attempts:
            try:
                timestamp_str = attempt.split(" - ")[0]
                timestamp = time.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                timestamps.append(time.mktime(timestamp))
            except:
                continue

        if not timestamps:
            self.time_ax.text(0.5, 0.5, 'No valid timestamp data', horizontalalignment='center',
                              verticalalignment='center', transform=self.time_ax.transAxes)
            self.time_canvas.draw()
            return

        # Sort timestamps
        timestamps.sort()

        # Bin the data into intervals (e.g., per minute)
        interval = 60  # seconds
        binned_data = defaultdict(int)
        for ts in timestamps:
            bucket = int(ts // interval) * interval
            binned_data[bucket] += 1

        # Prepare data for plotting
        sorted_buckets = sorted(binned_data.keys())
        counts = [binned_data[b] for b in sorted_buckets]
        times = [time.strftime("%H:%M", time.localtime(b)) for b in sorted_buckets]

        self.time_ax.clear()
        self.time_ax.plot(times, counts, marker='o', linestyle='-', color='blue')
        self.time_ax.set_xlabel("Time")
        self.time_ax.set_ylabel("Blocked Attempts")
        self.time_ax.set_title("Blocked Attempts Over Time")
        self.time_ax.tick_params(axis='x', rotation=45)
        self.time_fig.tight_layout()
        self.time_canvas.draw()

    def plot_top_sites_graph(self):
        """
        Plots a bar graph of the top blocked sites.
        """
        top_sites = self.get_top_blocked_sites()
        if not top_sites:
            self.sites_ax.text(0.5, 0.5, 'No data available', horizontalalignment='center',
                               verticalalignment='center', transform=self.sites_ax.transAxes)
            self.sites_canvas.draw()
            return

        sites, counts = zip(*top_sites)
        self.sites_ax.clear()
        self.sites_ax.bar(sites, counts, color='red')
        self.sites_ax.set_xlabel("Blocked Sites")
        self.sites_ax.set_ylabel("Number of Attempts")
        self.sites_ax.set_title("Top Blocked Sites")
        self.sites_ax.set_xticklabels(sites, rotation=45, ha='right')
        self.sites_fig.tight_layout()
        self.sites_canvas.draw()

# ------------------------------ Main Window ------------------------------ #

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Computer Network Firewall Browser")
        self.setGeometry(100, 100, 1400, 900)

        # Initialize blocked sites list and blocked attempts list
        self.blocked_sites = []
        self.blocked_attempts = []

        # Set up the main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        # --- Address Bar and Navigation Buttons ---
        nav_layout = QHBoxLayout()

        # Back Button
        back_button = QPushButton("<")
        back_button.setFixedWidth(40)
        back_button.clicked.connect(self.go_back)
        nav_layout.addWidget(back_button)

        # Forward Button
        forward_button = QPushButton(">")
        forward_button.setFixedWidth(40)
        forward_button.clicked.connect(self.go_forward)
        nav_layout.addWidget(forward_button)

        # Refresh Button
        refresh_button = QPushButton("⟳")
        refresh_button.setFixedWidth(40)
        refresh_button.clicked.connect(self.refresh_page)
        nav_layout.addWidget(refresh_button)

        # Home Button
        home_button = QPushButton("Home")
        home_button.clicked.connect(self.go_home)
        nav_layout.addWidget(home_button)

        # Address Bar
        self.address_bar = QLineEdit()
        self.address_bar.setPlaceholderText("Enter URL here...")
        self.address_bar.returnPressed.connect(self.load_url)
        nav_layout.addWidget(self.address_bar)

        # Go Button
        go_button = QPushButton("Go")
        go_button.clicked.connect(self.load_url)
        nav_layout.addWidget(go_button)

        # Show Status Button
        show_status_button = QPushButton("Show Status")
        show_status_button.clicked.connect(self.show_status)
        nav_layout.addWidget(show_status_button)

        # Show Statistics Button
        show_stats_button = QPushButton("Show Statistics")
        show_stats_button.clicked.connect(self.show_statistics)
        nav_layout.addWidget(show_stats_button)

        main_layout.addLayout(nav_layout)

        # --- Blocked Sites Bar ---
        blocked_layout = QHBoxLayout()
        blocked_label = QLabel("Blocked Sites:")
        blocked_label.setStyleSheet("font-weight: bold;")
        blocked_layout.addWidget(blocked_label)

        self.blocked_list_widget = QListWidget()
        self.blocked_list_widget.setFixedHeight(50)
        blocked_layout.addWidget(self.blocked_list_widget)

        # Remove Blocked Site Button
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_blocked_site)
        blocked_layout.addWidget(remove_button)

        main_layout.addLayout(blocked_layout)

        # --- Add Blocked Site ---
        add_blocked_layout = QHBoxLayout()
        self.add_blocked_input = QLineEdit()
        self.add_blocked_input.setPlaceholderText("Enter website to block (e.g., example.com)")
        add_blocked_layout.addWidget(self.add_blocked_input)

        add_blocked_button = QPushButton("Add to Blocked Sites")
        add_blocked_button.clicked.connect(self.add_blocked_site)
        add_blocked_layout.addWidget(add_blocked_button)

        main_layout.addLayout(add_blocked_layout)

        # --- Web Browser ---
        self.browser = QWebEngineView()
        self.browser.setContextMenuPolicy(Qt.NoContextMenu)  # Disable right-click context menu

        # Set custom page with firewall filtering
        self.browser_page = FirewallWebEnginePage(self.blocked_sites, self)
        self.browser.setPage(self.browser_page)

        main_layout.addWidget(self.browser)

        # --- Initialize with Home Page ---
        self.home_url = "https://www.google.com"
        self.browser.setUrl(QUrl(self.home_url))
        self.address_bar.setText(self.home_url)

    # --- Navigation Functions ---
    def go_back(self):
        self.browser.back()

    def go_forward(self):
        self.browser.forward()

    def refresh_page(self):
        self.browser.reload()

    def go_home(self):
        self.browser.setUrl(QUrl(self.home_url))
        self.address_bar.setText(self.home_url)

    def load_url(self):
        """
        Load the URL entered in the address bar after validation.
        """
        url_text = self.address_bar.text().strip()
        if not url_text:
            return

        # Add scheme if missing
        if not re.match(r'^https?://', url_text):
            url_text = 'http://' + url_text

        url = QUrl(url_text)
        if url.isValid():
            self.browser.setUrl(url)
        else:
            QMessageBox.warning(self, "Invalid URL", "The URL entered is not valid.")

    # --- Blocked Sites Management ---
    def add_blocked_site(self):
        """
        Add a new website to the blocked sites list.
        """
        site = self.add_blocked_input.text().strip()
        if not site:
            QMessageBox.warning(self, "Input Error", "Please enter a website to block.")
            return

        # Validate the website format
        if not re.match(r'^(www\.)?([A-Za-z0-9\-]+\.)+[A-Za-z]{2,}$', site):
            QMessageBox.warning(self, "Invalid Format", "Please enter a valid website format (e.g., example.com).")
            return

        if site.lower() in [s.lower() for s in self.blocked_sites]:
            QMessageBox.information(self, "Already Blocked", f"The website '{site}' is already in the blocked list.")
            return

        # Add to blocked sites
        self.blocked_sites.append(site)
        self.blocked_list_widget.addItem(site)
        self.add_blocked_input.clear()

        # Update the custom page's blocked sites
        self.browser_page.blocked_sites = self.blocked_sites

    def remove_blocked_site(self):
        """
        Remove the selected website from the blocked sites list.
        """
        selected_items = self.blocked_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selection Error", "Please select a website to remove.")
            return

        for item in selected_items:
            site = item.text()
            if site in self.blocked_sites:
                self.blocked_sites.remove(site)
            self.blocked_list_widget.takeItem(self.blocked_list_widget.row(item))

        # Update the custom page's blocked sites
        self.browser_page.blocked_sites = self.blocked_sites

    # --- Logging Blocked Attempts ---
    def log_blocked_attempt(self, attempted_url):
        """
        Log the blocked attempt with a timestamp.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_entry = f"{timestamp} - {attempted_url}"
        self.blocked_attempts.append(log_entry)

    # --- Status Dialog ---
    def show_status(self):
        """
        Display a status window showing all blocked attempts.
        """
        dialog = StatusDialog(self.blocked_attempts, self)
        dialog.exec_()

    # --- Statistics Dialog ---
    def show_statistics(self):
        """
        Display a statistics window with detailed information.
        """
        dialog = StatisticsDialog(self.blocked_attempts, self)
        dialog.exec_()

    # ------------------------------ Blocked Page Display ------------------------------ #
    def show_blocked_page(self, attempted_url):
        """
        Display a custom blocked page message.
        """
        html_content = f"""
        <html>
            <head>
                <title>Access Blocked</title>
            </head>
            <body style="background-color:#F44336; color:white; font-family:Arial, sans-serif; text-align:center;">
                <h1>Access to this website has been blocked by your firewall.</h1>
                <p><strong>Attempted URL:</strong> {attempted_url}</p>
            </body>
        </html>
        """
        self.browser.setHtml(html_content, QUrl(attempted_url))

# ------------------------------ Status Dialog ------------------------------ #

class StatusDialog(QDialog):
    """
    Dialog to display all blocked website access attempts.
    """
    def __init__(self, blocked_attempts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Firewall Status")
        self.setGeometry(150, 150, 600, 400)
        self.blocked_attempts = blocked_attempts
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Total blocked attempts
        total_blocked = len(self.blocked_attempts)
        total_label = QLabel(f"Total Blocked Attempts: {total_blocked}")
        total_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(total_label)

        # List of blocked URLs
        list_label = QLabel("Blocked Websites Accessed:")
        list_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(list_label)

        blocked_list = QListWidget()
        for attempt in self.blocked_attempts:
            blocked_list.addItem(attempt)
        layout.addWidget(blocked_list)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

# ------------------------------ Statistics Dialog ------------------------------ #

class StatisticsDialog(QDialog):
    """
    Dialog to display detailed statistics about blocked attempts.
    """
    def __init__(self, blocked_attempts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Firewall Statistics")
        self.setGeometry(200, 200, 800, 600)
        self.blocked_attempts = blocked_attempts
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Total blocked attempts
        total_blocked = len(self.blocked_attempts)
        total_label = QLabel(f"Total Blocked Attempts: {total_blocked}")
        total_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(total_label)

        # Top blocked sites
        top_sites = self.get_top_blocked_sites()
        top_sites_label = QLabel("Top Blocked Sites:")
        top_sites_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(top_sites_label)

        top_sites_list = QListWidget()
        for site, count in top_sites:
            top_sites_list.addItem(f"{site} - {count} times")
        layout.addWidget(top_sites_list)

        # Blocked attempts over time
        time_graph_label = QLabel("Blocked Attempts Over Time:")
        time_graph_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(time_graph_label)

        # Create a matplotlib figure for the time graph
        self.time_fig, self.time_ax = plt.subplots(figsize=(8, 3))
        self.time_canvas = FigureCanvas(self.time_fig)
        layout.addWidget(self.time_canvas)
        self.plot_blocked_over_time()

        # Top blocked sites graph
        sites_graph_label = QLabel("Top Blocked Sites Graph:")
        sites_graph_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(sites_graph_label)

        self.sites_fig, self.sites_ax = plt.subplots(figsize=(6, 4))
        self.sites_canvas = FigureCanvas(self.sites_fig)
        layout.addWidget(self.sites_canvas)
        self.plot_top_sites_graph()

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

    def get_top_blocked_sites(self):
        """
        Returns the top 5 blocked sites based on access attempts.
        """
        sites = [self.extract_site(attempt) for attempt in self.blocked_attempts]
        site_counts = Counter(sites)
        return site_counts.most_common(5)

    def extract_site(self, attempt):
        """
        Extract the domain from the blocked attempt URL.
        """
        try:
            url = attempt.split(" - ")[-1]
            domain = QUrl(url).host()
            return domain
        except:
            return "Unknown"

    def plot_blocked_over_time(self):
        """
        Plots blocked attempts over time.
        """
        if not self.blocked_attempts:
            self.time_ax.text(0.5, 0.5, 'No data available', horizontalalignment='center',
                              verticalalignment='center', transform=self.time_ax.transAxes)
            self.time_canvas.draw()
            return

        # Extract timestamps
        timestamps = []
        for attempt in self.blocked_attempts:
            try:
                timestamp_str = attempt.split(" - ")[0]
                timestamp = time.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                timestamps.append(time.mktime(timestamp))
            except:
                continue

        if not timestamps:
            self.time_ax.text(0.5, 0.5, 'No valid timestamp data', horizontalalignment='center',
                              verticalalignment='center', transform=self.time_ax.transAxes)
            self.time_canvas.draw()
            return

        # Sort timestamps
        timestamps.sort()

        # Bin the data into intervals (e.g., per minute)
        interval = 60  # seconds
        binned_data = defaultdict(int)
        for ts in timestamps:
            bucket = int(ts // interval) * interval
            binned_data[bucket] += 1

        # Prepare data for plotting
        sorted_buckets = sorted(binned_data.keys())
        counts = [binned_data[b] for b in sorted_buckets]
        times = [time.strftime("%H:%M", time.localtime(b)) for b in sorted_buckets]

        self.time_ax.clear()
        self.time_ax.plot(times, counts, marker='o', linestyle='-', color='blue')
        self.time_ax.set_xlabel("Time")
        self.time_ax.set_ylabel("Blocked Attempts")
        self.time_ax.set_title("Blocked Attempts Over Time")
        self.time_ax.tick_params(axis='x', rotation=45)
        self.time_fig.tight_layout()
        self.time_canvas.draw()

    def plot_top_sites_graph(self):
        """
        Plots a bar graph of the top blocked sites.
        """
        top_sites = self.get_top_blocked_sites()
        if not top_sites:
            self.sites_ax.text(0.5, 0.5, 'No data available', horizontalalignment='center',
                               verticalalignment='center', transform=self.sites_ax.transAxes)
            self.sites_canvas.draw()
            return

        sites, counts = zip(*top_sites)
        self.sites_ax.clear()
        self.sites_ax.bar(sites, counts, color='red')
        self.sites_ax.set_xlabel("Blocked Sites")
        self.sites_ax.set_ylabel("Number of Attempts")
        self.sites_ax.set_title("Top Blocked Sites")
        self.sites_ax.set_xticklabels(sites, rotation=45, ha='right')
        self.sites_fig.tight_layout()
        self.sites_canvas.draw()

# ------------------------------ Main Execution ------------------------------ #

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
