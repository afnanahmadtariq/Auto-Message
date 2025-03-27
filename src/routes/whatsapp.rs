use axum::{Router, routing::post, extract::Json};
use serde::{Deserialize, Serialize};
use mongodb::{Database, Client};
use crate::models::message::Message;
use chrono::Utc;

#[derive(Serialize, Deserialize)]
struct MessageRequest {
    contact: String,
    content: String,
}

async fn send_message(db: Database, Json(payload): Json<MessageRequest>) -> String {
    let collection = db.collection::<Message>("messages");
    
    let message = Message {
        user_id: "some_user_id".to_string(),
        contact: payload.contact,
        content: payload.content,
        timestamp: Utc::now().timestamp(),
    };

    collection.insert_one(message, None).await.unwrap();
    "Message sent".to_string()
}

pub fn routes(db: Client) -> Router {
    Router::new().route("/send", post(send_message))
}
