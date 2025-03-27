mod config;
mod db;
mod routes;
mod models;
mod utils;

use axum::{routing::post, Router};
use routes::{auth, whatsapp, scheduler};
use tower_http::cors::CorsLayer;
use std::net::SocketAddr;

#[tokio::main]
async fn main() {
    dotenv::dotenv().ok();
    let db = db::init().await.unwrap();

    let app = Router::new()
        .nest("/api/auth", auth::routes(db.clone()))
        .nest("/api/whatsapp", whatsapp::routes(db.clone()))
        .nest("/api/schedule", scheduler::routes(db.clone()))
        .layer(CorsLayer::permissive());

    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    println!("Server running on {}", addr);
    
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}
