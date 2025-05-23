import psutil
import os
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
## SLACK_WEBHOOK_URL = 'xxx'
CONFIG_FILE = "config.json"


def send_slack_notification(message, webhook):
    webhook = webhook
    """Send a message to Slack."""
    payload = {
        "remote_console_log": message
    }
    try:
        requests.post(webhook, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Slack notification: {e}")

def monitor_process(process_name, usersWebhook, output_text_box):
    """Monitor a specific process and send Slack notifications."""
    monitored_processes = {}

    try:
        while True:
            # Check for the specified process
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():  # Perform exact match
                     # Extract the script name or filepath
                    if len(proc.info['cmdline']) > 1:
                        script_path = proc.info['cmdline'][1]
                        script_name = os.path.basename(script_path)  # Extract only the file name
                    else:
                        script_name = "Unknown script"

                    if proc.info['pid'] not in monitored_processes:
                        monitored_processes[proc.info['pid']] = {
                            "process": proc,
                            "script_name": script_name
                        }
                        send_slack_notification(
                            f"Started monitoring process: {proc.info['name']} (PID: {proc.info['pid']})\n"
                            f"Script: {script_name}",
                            usersWebhook
                        )
                        print(
                            f"Started monitoring process: {proc.info['name']} (PID: {proc.info['pid']})\n"
                            f"Script: {script_name}"
                        )
                        # Update the GUI text box
                        output_text_box.delete(1.0, 5.0)  # Clear oldest message
                        output_text_box.config(state=tk.NORMAL)  # Make it editable
                        output_text_box.insert(tk.END, f"Started monitoring process: {proc.info['name']} (PID: {proc.info['pid']})\n"
                                                       f"Script: {script_name}\n")

            

            # Check if any monitored processes have finished
            finished_pids = []
            for pid, proc_info in monitored_processes.items():
                proc = proc_info["process"]
                script_name = proc_info["script_name"]
                if not psutil.pid_exists(pid):
                    try:
                        # Check if the process finished gracefully or errored out
                        exit_code = proc.wait(timeout=1)  # Wait for the process to terminate
                        status = "gracefully" if exit_code == 0 or 'None' else f"with error code {exit_code}"
                    except psutil.TimeoutExpired:
                        status = "with an unknown status (timeout while waiting for exit code)"

                    send_slack_notification(
                        f"Process '{proc.info['name']}' (PID: {pid}) has finished {status}.\n"
                        f"Script: {script_name}",
                        usersWebhook
                    )
                    print(
                        f"Process '{proc.info['name']}' (PID: {pid}) has finished {status}.\n"
                        f"Script: {script_name}"
                    )
                    # Update the GUI text box
                    output_text_box.delete(1.0, 5.0) # clear oldest message // i dont think i want to clear here so user can see the history
                    output_text_box.config(state=tk.NORMAL)  # Make it editable
                    output_text_box.insert(tk.END, f"Process '{proc.info['name']}' (PID: {pid}) has finished {status}.\n"
                        f"Script: {script_name}\n")
                    finished_pids.append(pid)
                    
                    

            # Remove finished processes from the monitored list
            for pid in finished_pids:
                del monitored_processes[pid]

            time.sleep(2)  # Check every 2 seconds
    except Exception as e:
        send_slack_notification(usersWebhook,f"Error while monitoring process: {e}")
        print(f"Error while monitoring process: {e}")

def start_process_monitoring(process_name, webhook, output_text_box):
    """Start monitoring the specified process."""
    if not process_name:
        messagebox.showerror("Error", "No process name specified!")
        return
    
    if not webhook:
        messagebox.showerror("Error", "No Slack webhook URL specified!")
        return
    # Validate the webhook URL
    if not webhook.startswith("https://hooks.slack.com/triggers/"):
        messagebox.showerror("Error", "Invalid Slack webhook URL!")
        return
    

    # Run the process monitoring in a separate thread to avoid blocking the GUI
    threading.Thread(target=monitor_process, args=(process_name, webhook,output_text_box), daemon=True).start()

     # Update the GUI text box
    output_text_box.config(state=tk.NORMAL)  # Make it editable
    output_text_box.delete(1.0, 5.0)  # Clear oldest message
    
    output_text_box.insert(tk.END, f"Looking for active {process_name} sessions... \n")
                                                     





def save_config(process_name, webhook):
    """Save the input values to a JSON file."""
    config = {
        "process_name": process_name,
        "webhook": webhook
    }
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file)

def load_config():
    """Load the input values from a JSON file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    return {"process_name": "", "webhook": ""}



def create_gui():
    """Create the tkinter GUI."""
    root = tk.Tk()
    root.title("Remote Console Log || Created by Zach End")

    config = load_config()

    # Process name input
    tk.Label(root, text="Process Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
    process_entry = tk.Entry(root, width=50)
    process_entry.grid(row=0, column=1, padx=10, pady=10)
    process_entry.insert(0, config.get("process_name", ""))  # Placeholder text

    # Process name input
    tk.Label(root, text="Slack Webhook Url:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
    webhook_entry = tk.Entry(root, width=50)
    webhook_entry.grid(row=1, column=1, padx=10, pady=10)
    webhook_entry.insert(0, config.get("webhook", ""))  # Placeholder text

    # Create a text box
    output_text_box = tk.Text(root, height=5, width=50, wrap="word")
    output_text_box.grid(row=3, column=0, columnspan=2, padx=10, pady=10)
    output_text_box.insert(tk.END, "Updates sent to slack will be displayed here...")
    output_text_box.config(state=tk.DISABLED)  # Make it read-only
    



    # Start button
    tk.Button(
        root,
        text="Start Monitoring",
        command=lambda: [
            save_config(process_entry.get(), webhook_entry.get()),  # Save values on button press
            start_process_monitoring(process_entry.get(), webhook_entry.get(), output_text_box)
        ],

    ).grid(row=2, column=0, columnspan=2, pady=20)
    

    root.mainloop()

if __name__ == "__main__":
    create_gui()