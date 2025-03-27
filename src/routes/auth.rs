use axum::{Router, routing::post, extract::Json};
use serde::{Deserialize, Serialize};
use mongodb::{Client, Database};
use crate::utils::{jwt::generate_jwt, hasher::verify_password};
use crate::models::user::User;

#[derive(Serialize, Deserialize)]
struct AuthRequest {
    email: String,
    password: String,
}

async fn login(db: Database, Json(payload): Json<AuthRequest>) -> String {
    let collection = db.collection::<User>("users");
    let user = collection.find_one(doc! { "email": &payload.email }, None).await.unwrap();

    if let Some(user) = user {
        if verify_password(&payload.password, &user.password) {
            return generate_jwt(&user.email);
        }
    }
    "Invalid credentials".to_string()
}

pub fn routes(db: Client) -> Router {
    Router::new().route("/login", post(login))
}
