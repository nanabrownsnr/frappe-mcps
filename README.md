# Frappe MCPs

This repository contains two Frappe-based applications plus MCP layers:

- `frappe-lending`
- `frappe-helpdesk`

The repo is organized as a mono-repo for deployment and publishing, while preserving each upstream source tree inside its own directory.

## Layout

- `compose.yaml`: root Docker Compose entrypoint
- `frappe-lending/`: Lending app and MCP
- `frappe-helpdesk/`: Helpdesk app and MCP

## Quick Start

Clone the repository, then copy env files for each app:

```powershell
Copy-Item .\frappe-lending\.env.example .\frappe-lending\.env
Copy-Item .\frappe-helpdesk\.env.example .\frappe-helpdesk\.env
```

Start both stacks from the repo root:

```powershell
docker compose up -d
```

Start a single stack directly:

```powershell
docker compose -f .\frappe-lending\docker-compose.yaml up -d
docker compose -f .\frappe-helpdesk\docker-compose.yaml up -d
```

## Default Endpoints

- Lending UI: `http://localhost:8000`
- Lending MCP: `http://localhost:8080/mcp`
- Helpdesk UI: `http://localhost:8100`
- Helpdesk MCP: `http://localhost:8081/mcp`

## Notes

- The first Helpdesk boot is slow because it initializes a full Frappe bench and builds frontend assets.
- The root `compose.yaml` uses Docker Compose `include`, so it expects a recent Docker Compose version.
