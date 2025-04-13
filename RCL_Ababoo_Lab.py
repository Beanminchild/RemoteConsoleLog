import psutil
import requests
import json
import time
import threading
import subprocess
import sys
import argparse
import tkinter as tk
from tkinter import filedialog, messagebox

# Replace with your actual webhook URL
SLACK_WEBHOOK_URL = 'xxx'

def send_slack_notification(message):
    """Send a message to Slack."""
    payload = {
        "remote_console_log": message
    }
    try:
        requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Slack notification: {e}")

def monitor_process(process_name):
    """Monitor a specific process and send Slack notifications."""
    monitored_processes = {}

    try:
        while True:
            # Check for the specified process
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                    script_name = " ".join(proc.info['cmdline'][1:]) if len(proc.info['cmdline']) > 1 else "Unknown script"
                    if proc.info['pid'] not in monitored_processes:
                        monitored_processes[proc.info['pid']] = {
                            "process": proc,
                            "script_name": script_name
                        }
                        send_slack_notification(
                            f"Started monitoring process: {proc.info['name']} (PID: {proc.info['pid']})\n"
                            f"Script: {script_name}"
                        )
                        print(
                            f"Started monitoring process: {proc.info['name']} (PID: {proc.info['pid']})\n"
                            f"Script: {script_name}"
                        )

            # Check if any monitored processes have finished
            finished_pids = []
            for pid, proc_info in monitored_processes.items():
                proc = proc_info["process"]
                script_name = proc_info["script_name"]
                if not psutil.pid_exists(pid):
                    try:
                        # Check if the process finished gracefully or errored out
                        exit_code = proc.wait(timeout=1)  # Wait for the process to terminate
                        status = "gracefully" if exit_code == 0 else f"with error code {exit_code}"
                    except psutil.TimeoutExpired:
                        status = "with an unknown status (timeout while waiting for exit code)"

                    send_slack_notification(
                        f"Process '{proc.info['name']}' (PID: {pid}) has finished {status}.\n"
                        f"Script: {script_name}"
                    )
                    print(
                        f"Process '{proc.info['name']}' (PID: {pid}) has finished {status}.\n"
                        f"Script: {script_name}"
                    )
                    finished_pids.append(pid)

            # Remove finished processes from the monitored list
            for pid in finished_pids:
                del monitored_processes[pid]

            time.sleep(2)  # Check every 2 seconds
    except Exception as e:
        send_slack_notification(f"Error while monitoring process: {e}")
        print(f"Error while monitoring process: {e}")

def start_process_monitoring(process_name):
    """Start monitoring the specified process."""
    if not process_name:
        messagebox.showerror("Error", "No process name specified!")
        return

    # Run the process monitoring in a separate thread to avoid blocking the GUI
    threading.Thread(target=monitor_process, args=(process_name,), daemon=True).start()

def create_gui():
    """Create the tkinter GUI."""
    root = tk.Tk()
    root.title("Process Monitor")

    # Process name input
    tk.Label(root, text="Process Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
    process_entry = tk.Entry(root, width=50)
    process_entry.grid(row=0, column=1, padx=10, pady=10)

    # Start button
    tk.Button(
        root,
        text="Start Monitoring",
        command=lambda: start_process_monitoring(process_entry.get())
    ).grid(row=1, column=0, columnspan=2, pady=20)

    root.mainloop()

if __name__ == "__main__":
    create_gui()