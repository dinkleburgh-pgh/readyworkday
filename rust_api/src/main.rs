use std::{env, net::SocketAddr, path::PathBuf, sync::Arc};

use axum::{
    http::{header::AUTHORIZATION, HeaderMap},
    extract::Path,
    extract::State,
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{delete, get, put},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use tokio::fs;
use tracing::{error, info};

#[derive(Clone)]
struct AppState {
    data_dir: Arc<PathBuf>,
    read_api_key: Option<Arc<String>>,
    write_api_key: Option<Arc<String>>,
}

#[derive(Copy, Clone)]
enum AccessLevel {
    Read,
    Write,
}

#[derive(Serialize)]
struct HealthResponse {
    status: &'static str,
    service: &'static str,
}

#[derive(Serialize)]
struct SaveResponse {
    status: &'static str,
    file: &'static str,
}

#[derive(Serialize)]
struct AssignmentSaveResponse {
    status: &'static str,
    assignment_type: &'static str,
    route: i64,
    assigned_truck: Option<i64>,
    reciprocal_updated: bool,
}

#[derive(Serialize)]
struct AssignmentSnapshotResponse {
    route_swap_assignments: Map<String, Value>,
    oos_spare_assignments: Map<String, Value>,
}

#[derive(Deserialize)]
struct RouteSwapRequest {
    route: i64,
    truck: i64,
    reciprocal: Option<bool>,
}

#[derive(Deserialize)]
struct OosSpareRequest {
    route: i64,
    spare_truck: i64,
}

#[derive(Serialize)]
struct ApiErrorBody {
    error: String,
}

struct ApiError {
    status: StatusCode,
    message: String,
}

impl ApiError {
    fn bad_request(message: impl Into<String>) -> Self {
        Self {
            status: StatusCode::BAD_REQUEST,
            message: message.into(),
        }
    }

    fn internal(message: impl Into<String>) -> Self {
        Self {
            status: StatusCode::INTERNAL_SERVER_ERROR,
            message: message.into(),
        }
    }

    fn unauthorized(message: impl Into<String>) -> Self {
        Self {
            status: StatusCode::UNAUTHORIZED,
            message: message.into(),
        }
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (
            self.status,
            Json(ApiErrorBody {
                error: self.message,
            }),
        )
            .into_response()
    }
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "truckapp_rust_api=info,axum=info".into()),
        )
        .init();

    let data_dir = env::var("TRUCKAPP_DATA_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."));

    let bind = env::var("RUST_API_BIND").unwrap_or_else(|_| "0.0.0.0:8787".to_string());
    let legacy_api_key = env::var("TRUCKAPP_API_KEY")
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .map(Arc::new);

    let mut read_api_key = env::var("TRUCKAPP_API_KEY_READ")
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .map(Arc::new);

    let mut write_api_key = env::var("TRUCKAPP_API_KEY_WRITE")
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .map(Arc::new);

    // Backward compatibility with legacy single-key configuration.
    if read_api_key.is_none() && write_api_key.is_none() {
        if let Some(single) = legacy_api_key.clone() {
            read_api_key = Some(single.clone());
            write_api_key = Some(single);
        }
    }

    // If only one role key is set, mirror it so all endpoints remain protected.
    if read_api_key.is_none() && write_api_key.is_some() {
        read_api_key = write_api_key.clone();
    }
    if write_api_key.is_none() && read_api_key.is_some() {
        write_api_key = read_api_key.clone();
    }

    if read_api_key.is_some() || write_api_key.is_some() {
        info!("Rust API auth enabled (role keys configured)");
    } else {
        info!("Rust API auth disabled (no API keys configured)");
    }

    let addr: SocketAddr = match bind.parse() {
        Ok(addr) => addr,
        Err(err) => {
            error!("Invalid RUST_API_BIND '{}': {}", bind, err);
            std::process::exit(1);
        }
    };

    let shared_state = AppState {
        data_dir: Arc::new(data_dir),
        read_api_key,
        write_api_key,
    };

    let app = Router::new()
        .route("/health", get(health))
        .route("/api/v1/state", get(get_state).put(put_state))
        .route("/api/v1/fleet", get(get_fleet).put(put_fleet))
        .route("/api/v1/assignments", get(get_assignments))
        .route("/api/v1/assignments/route-swaps", put(put_route_swap))
        .route(
            "/api/v1/assignments/route-swaps/:route",
            delete(delete_route_swap),
        )
        .route("/api/v1/assignments/oos-spares", put(put_oos_spare))
        .route(
            "/api/v1/assignments/oos-spares/:route",
            delete(delete_oos_spare),
        )
        .with_state(shared_state);

    info!("Rust API listening on {}", addr);

    match tokio::net::TcpListener::bind(addr).await {
        Ok(listener) => {
            if let Err(err) = axum::serve(listener, app).await {
                error!("Server error: {}", err);
            }
        }
        Err(err) => {
            error!("Failed to bind {}: {}", addr, err);
            std::process::exit(1);
        }
    }
}

async fn health() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok",
        service: "truckapp-rust-api",
    })
}

async fn get_state(State(app): State<AppState>, headers: HeaderMap) -> Result<Json<Value>, ApiError> {
    require_api_key(&app, &headers, AccessLevel::Read)?;
    let state = read_json_file(&app.data_dir, ".truck_state.json").await?;
    Ok(Json(state))
}

async fn get_fleet(State(app): State<AppState>, headers: HeaderMap) -> Result<Json<Value>, ApiError> {
    require_api_key(&app, &headers, AccessLevel::Read)?;
    let fleet = read_json_file(&app.data_dir, "truck_fleet.json").await?;
    Ok(Json(fleet))
}

async fn put_state(
    State(app): State<AppState>,
    headers: HeaderMap,
    Json(payload): Json<Value>,
) -> Result<(StatusCode, Json<SaveResponse>), ApiError> {
    require_api_key(&app, &headers, AccessLevel::Write)?;
    write_json_file(&app.data_dir, ".truck_state.json", &payload).await?;
    Ok((
        StatusCode::OK,
        Json(SaveResponse {
            status: "saved",
            file: ".truck_state.json",
        }),
    ))
}

async fn put_fleet(
    State(app): State<AppState>,
    headers: HeaderMap,
    Json(payload): Json<Value>,
) -> Result<(StatusCode, Json<SaveResponse>), ApiError> {
    require_api_key(&app, &headers, AccessLevel::Write)?;
    write_json_file(&app.data_dir, "truck_fleet.json", &payload).await?;
    Ok((
        StatusCode::OK,
        Json(SaveResponse {
            status: "saved",
            file: "truck_fleet.json",
        }),
    ))
}

async fn get_assignments(
    State(app): State<AppState>,
    headers: HeaderMap,
) -> Result<Json<AssignmentSnapshotResponse>, ApiError> {
    require_api_key(&app, &headers, AccessLevel::Read)?;
    let mut state_json = read_state_file(&app.data_dir).await?;
    let root = expect_root_object_mut(&mut state_json)?;

    let route_swaps = ensure_object_map(root, "route_swap_assignments")?.clone();
    let oos_spares = ensure_object_map(root, "oos_spare_assignments")?.clone();

    Ok(Json(AssignmentSnapshotResponse {
        route_swap_assignments: route_swaps,
        oos_spare_assignments: oos_spares,
    }))
}

async fn put_route_swap(
    State(app): State<AppState>,
    headers: HeaderMap,
    Json(payload): Json<RouteSwapRequest>,
) -> Result<(StatusCode, Json<AssignmentSaveResponse>), ApiError> {
    require_api_key(&app, &headers, AccessLevel::Write)?;
    let route = positive_id(payload.route, "route")?;
    let truck = positive_id(payload.truck, "truck")?;
    if route == truck {
        return Err(ApiError::bad_request("route and truck cannot be the same"));
    }

    let reciprocal = payload.reciprocal.unwrap_or(false);
    let mut state_json = read_state_file(&app.data_dir).await?;
    {
        let root = expect_root_object_mut(&mut state_json)?;
        let swaps = ensure_object_map(root, "route_swap_assignments")?;

        // Keep route->truck mapping one-to-one by removing conflicting routes and truck usage.
        remove_route_or_truck_conflicts(swaps, route, truck);
        swaps.insert(route.to_string(), Value::from(truck));

        if reciprocal {
            remove_route_or_truck_conflicts(swaps, truck, route);
            swaps.insert(truck.to_string(), Value::from(route));
        }
    }

    write_state_file_value(&app.data_dir, &state_json).await?;
    Ok((
        StatusCode::OK,
        Json(AssignmentSaveResponse {
            status: "saved",
            assignment_type: "route_swap",
            route,
            assigned_truck: Some(truck),
            reciprocal_updated: reciprocal,
        }),
    ))
}

async fn delete_route_swap(
    State(app): State<AppState>,
    headers: HeaderMap,
    Path(route): Path<i64>,
) -> Result<(StatusCode, Json<AssignmentSaveResponse>), ApiError> {
    require_api_key(&app, &headers, AccessLevel::Write)?;
    let route = positive_id(route, "route")?;
    let mut state_json = read_state_file(&app.data_dir).await?;

    let mut reciprocal_removed = false;
    {
        let root = expect_root_object_mut(&mut state_json)?;
        let swaps = ensure_object_map(root, "route_swap_assignments")?;

        let removed_target = swaps
            .remove(&route.to_string())
            .and_then(|v| v.as_i64());

        if let Some(other_route) = removed_target {
            if swaps.get(&other_route.to_string()).and_then(|v| v.as_i64()) == Some(route) {
                swaps.remove(&other_route.to_string());
                reciprocal_removed = true;
            }
        }
    }

    write_state_file_value(&app.data_dir, &state_json).await?;
    Ok((
        StatusCode::OK,
        Json(AssignmentSaveResponse {
            status: "saved",
            assignment_type: "route_swap",
            route,
            assigned_truck: None,
            reciprocal_updated: reciprocal_removed,
        }),
    ))
}

async fn put_oos_spare(
    State(app): State<AppState>,
    headers: HeaderMap,
    Json(payload): Json<OosSpareRequest>,
) -> Result<(StatusCode, Json<AssignmentSaveResponse>), ApiError> {
    require_api_key(&app, &headers, AccessLevel::Write)?;
    let route = positive_id(payload.route, "route")?;
    let spare_truck = positive_id(payload.spare_truck, "spare_truck")?;
    if route == spare_truck {
        return Err(ApiError::bad_request("route and spare_truck cannot be the same"));
    }

    let mut state_json = read_state_file(&app.data_dir).await?;
    {
        let root = expect_root_object_mut(&mut state_json)?;
        let oos_map = ensure_object_map(root, "oos_spare_assignments")?;

        // Keep spare assignment one-to-one by removing any route currently using this spare.
        remove_oos_spare_conflicts(oos_map, route, spare_truck);
        oos_map.insert(route.to_string(), Value::from(spare_truck));
    }

    write_state_file_value(&app.data_dir, &state_json).await?;
    Ok((
        StatusCode::OK,
        Json(AssignmentSaveResponse {
            status: "saved",
            assignment_type: "oos_spare",
            route,
            assigned_truck: Some(spare_truck),
            reciprocal_updated: false,
        }),
    ))
}

async fn delete_oos_spare(
    State(app): State<AppState>,
    headers: HeaderMap,
    Path(route): Path<i64>,
) -> Result<(StatusCode, Json<AssignmentSaveResponse>), ApiError> {
    require_api_key(&app, &headers, AccessLevel::Write)?;
    let route = positive_id(route, "route")?;
    let mut state_json = read_state_file(&app.data_dir).await?;
    {
        let root = expect_root_object_mut(&mut state_json)?;
        let oos_map = ensure_object_map(root, "oos_spare_assignments")?;
        oos_map.remove(&route.to_string());
    }

    write_state_file_value(&app.data_dir, &state_json).await?;
    Ok((
        StatusCode::OK,
        Json(AssignmentSaveResponse {
            status: "saved",
            assignment_type: "oos_spare",
            route,
            assigned_truck: None,
            reciprocal_updated: false,
        }),
    ))
}

async fn read_json_file(base_dir: &PathBuf, file_name: &str) -> Result<Value, ApiError> {
    if file_name.trim().is_empty() {
        return Err(ApiError::bad_request("file name cannot be empty"));
    }

    let path = base_dir.join(file_name);
    let text = fs::read_to_string(&path).await.map_err(|err| {
        ApiError::internal(format!("failed reading {}: {}", path.display(), err))
    })?;

    serde_json::from_str::<Value>(&text)
        .map_err(|err| ApiError::internal(format!("invalid JSON in {}: {}", path.display(), err)))
}

async fn read_state_file(base_dir: &PathBuf) -> Result<Value, ApiError> {
    read_json_file(base_dir, ".truck_state.json").await
}

async fn write_state_file_value(base_dir: &PathBuf, payload: &Value) -> Result<(), ApiError> {
    write_json_file(base_dir, ".truck_state.json", payload).await
}

fn expect_root_object_mut(value: &mut Value) -> Result<&mut Map<String, Value>, ApiError> {
    value
        .as_object_mut()
        .ok_or_else(|| ApiError::internal("state root JSON is not an object"))
}

fn ensure_object_map<'a>(
    root: &'a mut Map<String, Value>,
    key: &'static str,
) -> Result<&'a mut Map<String, Value>, ApiError> {
    let entry = root
        .entry(key.to_string())
        .or_insert_with(|| Value::Object(Map::new()));
    if !entry.is_object() {
        *entry = Value::Object(Map::new());
    }
    entry
        .as_object_mut()
        .ok_or_else(|| ApiError::internal(format!("{} should be an object", key)))
}

fn positive_id(id: i64, field: &'static str) -> Result<i64, ApiError> {
    if id <= 0 {
        return Err(ApiError::bad_request(format!("{} must be a positive integer", field)));
    }
    Ok(id)
}

fn remove_route_or_truck_conflicts(swaps: &mut Map<String, Value>, route: i64, truck: i64) {
    let route_key = route.to_string();
    let truck_key = truck.to_string();
    let mut to_remove: Vec<String> = Vec::new();

    for (key, value) in swaps.iter() {
        let key_num = key.parse::<i64>().ok();
        let value_num = value.as_i64();

        if key_num == Some(route)
            || key_num == Some(truck)
            || value_num == Some(route)
            || value_num == Some(truck)
        {
            to_remove.push(key.clone());
        }
    }

    for key in to_remove {
        swaps.remove(&key);
    }

    // Ensure direct keys are clear before insert.
    swaps.remove(&route_key);
    swaps.remove(&truck_key);
}

fn remove_oos_spare_conflicts(oos_map: &mut Map<String, Value>, route: i64, spare_truck: i64) {
    let route_key = route.to_string();
    let mut to_remove: Vec<String> = Vec::new();

    for (key, value) in oos_map.iter() {
        let key_num = key.parse::<i64>().ok();
        let value_num = value.as_i64();
        if key_num == Some(route) || value_num == Some(spare_truck) {
            to_remove.push(key.clone());
        }
    }

    for key in to_remove {
        oos_map.remove(&key);
    }

    oos_map.remove(&route_key);
}

async fn write_json_file(base_dir: &PathBuf, file_name: &str, payload: &Value) -> Result<(), ApiError> {
    if file_name.trim().is_empty() {
        return Err(ApiError::bad_request("file name cannot be empty"));
    }

    let path = base_dir.join(file_name);
    let body = serde_json::to_string_pretty(payload)
        .map_err(|err| ApiError::internal(format!("failed serializing JSON for {}: {}", path.display(), err)))?;
    let body = format!("{}\n", body);

    fs::write(&path, body)
        .await
        .map_err(|err| ApiError::internal(format!("failed writing {}: {}", path.display(), err)))
}

fn require_api_key(app: &AppState, headers: &HeaderMap, level: AccessLevel) -> Result<(), ApiError> {
    let expected_read = app.read_api_key.as_ref().map(|k| k.as_str());
    let expected_write = app.write_api_key.as_ref().map(|k| k.as_str());

    if expected_read.is_none() && expected_write.is_none() {
        return Ok(());
    }

    let header_key = headers
        .get("x-api-key")
        .and_then(|v| v.to_str().ok())
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());

    let bearer_key = headers
        .get(AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .and_then(|raw| raw.split_once(char::is_whitespace))
        .and_then(|(scheme, token)| {
            if scheme.eq_ignore_ascii_case("Bearer") {
                Some(token)
            } else {
                None
            }
        })
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());

    let provided = header_key.or(bearer_key);
    let allowed = match level {
        AccessLevel::Read => {
            provided.is_some()
                && (provided == expected_read || provided == expected_write)
        }
        AccessLevel::Write => {
            provided.is_some() && provided == expected_write
        }
    };

    if allowed {
        Ok(())
    } else {
        let msg = match level {
            AccessLevel::Read => {
                "missing or invalid read key; provide x-api-key or Authorization: Bearer <read-or-write-key>"
            }
            AccessLevel::Write => {
                "missing or invalid write key; provide x-api-key or Authorization: Bearer <write-key>"
            }
        };
        Err(ApiError::unauthorized(msg))
    }
}
