# TruckApp Streamlit Deployment (code-server/TrueNAS)

## Quick Start

1. Clone the repo:
   ```sh
   git clone <your-repo-url>
   cd TruckApp
   ```
2. Create and activate the virtual environment:
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run the app in the background:
   ```sh
   ./run_streamlit.sh
   ```
4. Access the app at `http://<your-server-ip>:8501`

## Auto-Start on Reboot (optional)
Add this to your crontab:
```sh
@reboot /path/to/TruckApp/run_streamlit.sh
```

## Notes
- All state/log files are stored in `.data/` for portability.
- Make sure port 8501 is open on your firewall/router.
- The run_streamlit.sh script will create the venv and install requirements if missing.
- For troubleshooting, check `.data/streamlit.log` for logs.
