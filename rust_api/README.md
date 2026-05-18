# Rust API Layer (TruckApp)

This service exposes selected TruckApp JSON state as HTTP endpoints for mobile and external clients.

## Endpoints

- `GET /health` -> service status
- `GET /api/v1/state` -> contents of `.truck_state.json`
- `GET /api/v1/fleet` -> contents of `truck_fleet.json`
- `PUT /api/v1/state` -> overwrite `.truck_state.json` with request JSON body
- `PUT /api/v1/fleet` -> overwrite `truck_fleet.json` with request JSON body
- `GET /api/v1/assignments` -> current `route_swap_assignments` + `oos_spare_assignments`
- `PUT /api/v1/assignments/route-swaps` -> set a route swap
- `DELETE /api/v1/assignments/route-swaps/:route` -> remove a route swap by route
- `PUT /api/v1/assignments/oos-spares` -> set OOS spare assignment
- `DELETE /api/v1/assignments/oos-spares/:route` -> remove OOS spare assignment by route

## Configuration

- `TRUCKAPP_DATA_DIR` (default: `.`)
- `RUST_API_BIND` (default: `0.0.0.0:8787`)
- `TRUCKAPP_API_KEY_READ` (optional read key)
- `TRUCKAPP_API_KEY_WRITE` (optional write key)
- `TRUCKAPP_API_KEY` (legacy fallback single key)

Auth precedence:

- If `TRUCKAPP_API_KEY_READ` and `TRUCKAPP_API_KEY_WRITE` are both unset, `TRUCKAPP_API_KEY` is used for both.
- If only one role key is set, it is mirrored to both read and write so all endpoints stay protected.
- `GET /health` remains public.
- `GET /api/v1/*` accepts read or write key.
- `PUT/DELETE /api/v1/*` requires write key.

Auth headers (either one):

- `x-api-key: <your-key>`
- `Authorization: Bearer <your-key>`

Example write:

```bash
curl -X PUT http://localhost:8787/api/v1/state \
	-H "x-api-key: change-me" \
	-H "Content-Type: application/json" \
	--data-binary @data/.truck_state.json
```

Targeted assignment writes:

```bash
curl -X PUT http://localhost:8787/api/v1/assignments/route-swaps \
	-H "x-api-key: change-me" \
	-H "Content-Type: application/json" \
	-d '{"route":83,"truck":1,"reciprocal":true}'

curl -X DELETE http://localhost:8787/api/v1/assignments/route-swaps/83 \
	-H "x-api-key: change-me"

curl -X PUT http://localhost:8787/api/v1/assignments/oos-spares \
	-H "x-api-key: change-me" \
	-H "Content-Type: application/json" \
	-d '{"route":83,"spare_truck":140}'

curl -X DELETE http://localhost:8787/api/v1/assignments/oos-spares/83 \
	-H "x-api-key: change-me"
```

## Run locally

```bash
cd rust_api
cargo run
```

Or point to your data dir explicitly:

```bash
TRUCKAPP_DATA_DIR=.. cargo run
```
