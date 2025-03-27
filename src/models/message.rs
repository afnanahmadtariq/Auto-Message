use serde::{Deserialize, Serialize};
use chrono::Utc;

#[derive(Serialize, Deserialize, Debug)]
pub struct Message {
    pub user_id: String,
    pub contact: String,
    pub content: String,
    pub timestamp: i64,
}
