# Android REST Targets

This file defines the targeted assignment endpoints for your Android app.

## Base URL

- Emulator: http://10.0.2.2:8787
- Device on LAN: http://<your-pc-lan-ip>:8787

## Environment Metadata

Set these in root `.env` for Docker Compose:

```env
RUST_API_PORT=8787
TRUCKAPP_API_KEY_READ=change-me-read-key
TRUCKAPP_API_KEY_WRITE=change-me-write-key
TRUCKAPP_API_KEY=
```

- `TRUCKAPP_API_KEY` is a legacy fallback and should stay blank when using role keys.

## Endpoints

- `GET /health`
- `GET /api/v1/state`
- `GET /api/v1/fleet`
- `GET /api/v1/assignments`
- `PUT /api/v1/assignments/route-swaps`
- `DELETE /api/v1/assignments/route-swaps/{route}`
- `PUT /api/v1/assignments/oos-spares`
- `DELETE /api/v1/assignments/oos-spares/{route}`

## Authentication

When API auth is configured, all `/api/v1/*` endpoints require one of these headers:

- `x-api-key: <your-key>`
- `Authorization: Bearer <your-key>`

Role behavior:

- Reads (`GET /api/v1/*`): read key or write key
- Writes (`PUT/DELETE /api/v1/*`): write key only

Recommended for Android: attach `x-api-key` with an OkHttp interceptor.

## Request Models

### Route swap upsert

PUT /api/v1/assignments/route-swaps

```json
{
  "route": 83,
  "truck": 1,
  "reciprocal": true
}
```

- `route`: target route to cover
- `truck`: truck now covering that route
- `reciprocal` (optional): when true, also maps truck -> route for two-way ownership

### OOS spare upsert

PUT /api/v1/assignments/oos-spares

```json
{
  "route": 83,
  "spare_truck": 140
}
```

- `route`: OOS route
- `spare_truck`: spare truck assigned to cover

## Response Models

### Assignment snapshot

GET /api/v1/assignments

```json
{
  "route_swap_assignments": {
    "83": 1,
    "1": 83
  },
  "oos_spare_assignments": {
    "52": 140
  }
}
```

### Save result

```json
{
  "status": "saved",
  "assignment_type": "route_swap",
  "route": 83,
  "assigned_truck": 1,
  "reciprocal_updated": true
}
```

## Retrofit Targets

```kotlin
interface TruckApi {
    @GET("/health")
    suspend fun health(): HealthResponse

    @GET("/api/v1/assignments")
    suspend fun assignments(): AssignmentsResponse

    @PUT("/api/v1/assignments/route-swaps")
    suspend fun upsertRouteSwap(@Body payload: RouteSwapRequest): SaveResponse

    @DELETE("/api/v1/assignments/route-swaps/{route}")
    suspend fun deleteRouteSwap(@Path("route") route: Int): SaveResponse

    @PUT("/api/v1/assignments/oos-spares")
    suspend fun upsertOosSpare(@Body payload: OosSpareRequest): SaveResponse

    @DELETE("/api/v1/assignments/oos-spares/{route}")
    suspend fun deleteOosSpare(@Path("route") route: Int): SaveResponse
}
```

Optional header interceptor:

```kotlin
class ApiKeyInterceptor(private val apiKey: String) : Interceptor {
  override fun intercept(chain: Interceptor.Chain): Response {
    val request = chain.request().newBuilder()
      .addHeader("x-api-key", apiKey)
      .build()
    return chain.proceed(request)
  }
}
```

If you use separate clients, you can create:

- `readClient` with read key for GET calls
- `writeClient` with write key for PUT/DELETE calls

## Notes

- Route and truck IDs must be positive integers.
- Route swap and OOS spare writes only update the assignment maps in `.truck_state.json`.
- If the app runs over HTTP in dev, allow cleartext traffic in Android manifest/network config.
