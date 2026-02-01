#!/usr/bin/env python3
"""
Letterboxd Watchlist Menu Bar App

A simple menu bar app that shows your watchlist streaming availability.
Click the film icon to refresh and view your watchlist.
"""

import rumps
import subprocess
import os
import threading

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKER_SCRIPT = os.path.join(SCRIPT_DIR, "watchlist_checker.py")
HTML_FILE = os.path.join(SCRIPT_DIR, "watchlist.html")


class WatchlistApp(rumps.App):
    def __init__(self):
        super(WatchlistApp, self).__init__(
            "Watchlist",
            icon=None,  # Will use emoji as title
            title="🎬",
            quit_button=None  # We'll add our own
        )
        self.menu = [
            rumps.MenuItem("Check Watchlist", callback=self.check_watchlist),
            rumps.MenuItem("Open Last Results", callback=self.open_results),
            None,  # Separator
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]
        self.is_checking = False

    def check_watchlist(self, _):
        """Run the watchlist checker and open results."""
        if self.is_checking:
            rumps.notification(
                title="Watchlist Checker",
                subtitle="Already running",
                message="Please wait for the current check to finish."
            )
            return

        self.is_checking = True
        self.title = "⏳"  # Show loading indicator

        # Run in background thread to not block the UI
        thread = threading.Thread(target=self._run_checker)
        thread.daemon = True
        thread.start()

    def _run_checker(self):
        """Run the checker script in background."""
        try:
            result = subprocess.run(
                ["python3", CHECKER_SCRIPT],
                cwd=SCRIPT_DIR,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                rumps.notification(
                    title="Watchlist Updated",
                    subtitle="",
                    message="Your streaming guide is ready!"
                )
            else:
                rumps.notification(
                    title="Error",
                    subtitle="",
                    message="Failed to check watchlist. See terminal for details."
                )
                print(result.stderr)

        except subprocess.TimeoutExpired:
            rumps.notification(
                title="Timeout",
                subtitle="",
                message="Watchlist check took too long."
            )
        except Exception as e:
            rumps.notification(
                title="Error",
                subtitle="",
                message=str(e)
            )
        finally:
            self.is_checking = False
            self.title = "🎬"

    def open_results(self, _):
        """Open the last generated HTML file."""
        if os.path.exists(HTML_FILE):
            subprocess.run(["open", HTML_FILE])
        else:
            rumps.notification(
                title="No Results",
                subtitle="",
                message="Run 'Check Watchlist' first to generate results."
            )

    def quit_app(self, _):
        """Quit the app."""
        rumps.quit_application()


if __name__ == "__main__":
    WatchlistApp().run()
