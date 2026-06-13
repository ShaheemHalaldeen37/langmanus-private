# LangManus — Setup & Running Instructions

## Prerequisites

- Python 3.11 or higher
- A Groq API key (free tier works) — [console.groq.com](https://console.groq.com)
- A Tavily API key — [tavily.com](https://tavily.com)
- Google Chrome (used by the browser agent)

---

## OS compatibility

| OS | Setup script |
|---|---|
| Linux / macOS | `bash setup.sh` |
| Windows (native) | `.\setup.ps1` in PowerShell (see note below) |
| Windows via WSL2 | `bash setup.sh` — identical to Linux |

> **Windows users — recommended: WSL2**
> WSL2 (Windows Subsystem for Linux) runs a real Linux environment inside Windows and is the easiest path. Install it once with `wsl --install` in an Administrator PowerShell, then open a WSL terminal and follow the Linux/macOS steps below.
>
> **Windows users — native PowerShell**
> If you prefer not to use WSL2, use `setup.ps1` instead of `setup.sh`. You may need to allow script execution first (run once as Administrator):
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

---

## 1. Clone & enter the project

```bash
git clone <repo-url>
cd langmanus-private
```

---

## 2. Configure environment variables

Copy the example file and fill in your API keys:

```bash
# Linux / macOS / WSL2
cp .env.example .env

# Windows (PowerShell)
copy .env.example .env
```

Open `.env` and set the following:

| Variable | Description |
|---|---|
| `REASONING_API_KEY` | Your Groq API key (`gsk_...`) |
| `BASIC_API_KEY` | Same Groq API key |
| `VL_API_KEY` | Same Groq API key |
| `TAVILY_API_KEY` | Your Tavily API key (`tvly-...`) |

The model names and base URLs are pre-filled in `.env.example` and work as-is for Groq.

---

## 3. Create the virtual environment and install dependencies

Run the setup script once from the project root:

```bash
# Linux / macOS / WSL2
bash setup.sh

# Windows (PowerShell)
.\setup.ps1
```

This will:
- Create a `.venv` directory
- Install all Python dependencies from `pyproject.toml`
- Install the Playwright Chromium browser for the browser agent

---

## 4. Start the backend server

Activate the virtual environment, then start the FastAPI server:

```bash
# Linux / macOS / WSL2
source .venv/bin/activate
python server.py

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
python server.py
```

The server runs on **http://localhost:8000**. You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

---

## 5. Start the web UI

Open a **new terminal**, then serve the UI from the `web_ui/` directory:

```bash
# Linux / macOS / WSL2
cd web_ui
python3 -m http.server 3000

# Windows (PowerShell)
cd web_ui
python -m http.server 3000
```

The UI is available at **http://localhost:3000**

---

## Quick-start summary

```bash
# Terminal 1 — backend (Linux / macOS / WSL2)
source .venv/bin/activate && python server.py

# Terminal 2 — frontend
cd web_ui && python3 -m http.server 3000
```

```powershell
# Terminal 1 — backend (Windows PowerShell)
.venv\Scripts\Activate.ps1; python server.py

# Terminal 2 — frontend
cd web_ui; python -m http.server 3000
```

Then open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Notes

- The backend must be running before you submit a query in the UI.
- The Groq free tier has rate limits (6 000 tokens/min per model). Delays between agent calls are built in to handle this automatically.
- The `404` error for `favicon.ico` in the web UI terminal is harmless — browsers request it automatically.
- To stop either process press `Ctrl+C` in its terminal.
