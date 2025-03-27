use axum::{Router, routing::post, extract::Json};
use serde::{Deserialize, Serialize};
use mongodb::{Database, Client};
use chrono::Utc;

#[derive(Serialize, Deserialize)]
struct ScheduleRequest {
    contact: String,
    content: String,
    timestamp: i64,
}

async fn schedule_message(db: Database, Json(payload): Json<ScheduleRequest>) -> String {
    let collection = db.collection::<Message>("scheduled_messages");

    let message = Message {
        user_id: "some_user_id".to_string(),
        contact: payload.contact,
        content: payload.content,
        timestamp: payload.timestamp,
    };

    collection.insert_one(message, None).await.unwrap();
    "Message scheduled".to_string()
}

pub fn routes(db: Client) -> Router {
    Router::new().route("/schedule", post(schedule_message))
}
