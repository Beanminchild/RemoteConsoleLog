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
    """Monitor a specific process or its child processes (e.g., RStudio and Rscript)."""
    monitored_processes = {}

    try:
        while True:
            # Check if the user is monitoring RStudio
            if process_name.lower() == "rstudio":
                # Look for the RStudio process
                rstudio_process = None
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'] and 'rstudio' in proc.info['name'].lower():
                        rstudio_process = proc
                        break

                if not rstudio_process:
                    send_slack_notification("RStudio is not running.", usersWebhook)
                    output_text_box.config(state=tk.NORMAL)
                    output_text_box.delete(1.0, 5.0) # clear oldest message
                    
                    output_text_box.insert(tk.END, "RStudio is not running.\n")
                    ##output_text_box.config(state=tk.DISABLED)
                    print("RStudio is not running.")
                    # Wait for a while before checking again

                    time.sleep(60)  # Check every 60 seconds
                    continue

                # Monitor child processes of RStudio
                for child in rstudio_process.children(recursive=True):
                    if child.pid not in monitored_processes and 'rscript' in child.name().lower():
                        monitored_processes[child.pid] = child
                        send_slack_notification(
                            f"Started monitoring Rscript process: {child.name()} (PID: {child.pid})",
                            usersWebhook
                        )
                        print(f"Started monitoring Rscript process: {child.name()} (PID: {child.pid})")
                        output_text_box.delete(1.0, 5.0) # clear oldest message
                        output_text_box.config(state=tk.NORMAL)
                        output_text_box.insert(tk.END, f"Started monitoring Rscript process: {child.name()} (PID: {child.pid})\n")
                        ##output_text_box.config(state=tk.DISABLED)

            else:
                # Monitor the specified process directly
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
                                f"Script: {script_name}",
                                usersWebhook
                            )
                            print(
                                f"Started monitoring process: {proc.info['name']} (PID: {proc.info['pid']})\n"
                                f"Script: {script_name}"
                            )
                            output_text_box.delete(1.0, 5.0) # clear oldest message
                            # Update the text box with the new process information
                            output_text_box.config(state=tk.NORMAL)
                            output_text_box.insert(tk.END, f"Started monitoring process: {proc.info['name']} (PID: {proc.info['pid']})\n"
                                f"Script: {script_name}\n")
                            ##output_text_box.config(state=tk.DISABLED)

            # Check if any monitored processes have finished
            finished_pids = []
            for pid, proc_info in monitored_processes.items():
                if isinstance(proc_info, psutil.Process):  # For RStudio child processes
                    proc = proc_info
                    if not psutil.pid_exists(pid):
                        send_slack_notification(f"Rscript process (PID: {pid}) has finished.", usersWebhook)
                        print(f"Rscript process (PID: {pid}) has finished.")
                        output_text_box.delete(1.0, 5.0) # clear oldest message

                        output_text_box.config(state=tk.NORMAL)
                        output_text_box.insert(tk.END, f"Rscript process (PID: {pid}) has finished.\n")
                        ##output_text_box.config(state=tk.DISABLED)
                        finished_pids.append(pid)
                else:  # For directly monitored processes
                    proc = proc_info["process"]
                    script_name = proc_info["script_name"]
                    if not psutil.pid_exists(pid):
                        try:
                            exit_code = proc.wait(timeout=1)
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
                        output_text_box.delete(1.0, 5.0) # clear oldest message
                        output_text_box.config(state=tk.NORMAL)
                        output_text_box.insert(tk.END, f"Process '{proc.info['name']}' (PID: {pid}) has finished {status}.\n"
                            f"Script: {script_name}\n")
                        ##output_text_box.config(state=tk.DISABLED)
                        finished_pids.append(pid)

            # Remove finished processes from the monitored list
            for pid in finished_pids:
                del monitored_processes[pid]

            time.sleep(2)  # Check every 2 seconds
    except Exception as e:
        send_slack_notification(f"Error while monitoring process: {e}", usersWebhook)
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
    # Validate the process name
    if not process_name.isalnum():
        messagebox.showerror("Error", "Invalid process name! Only alphanumeric characters are allowed.")
        return

    # Run the process monitoring in a separate thread to avoid blocking the GUI
    threading.Thread(target=monitor_process, args=(process_name, webhook,output_text_box), daemon=True).start()


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
    root.title("Remote Console Log")

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
    output_text_box.insert(tk.END, "Slack updates will also be displayed here...")
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