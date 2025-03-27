use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct User {
    pub email: String,
    pub password: String,
    pub two_factor_enabled: bool,
    pub two_factor_secret: Option<String>,
}
