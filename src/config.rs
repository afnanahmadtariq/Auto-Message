use std::env;

pub struct Config {
    pub mongo_uri: String,
    pub jwt_secret: String,
}

impl Config {
    pub fn from_env() -> Self {
        dotenv::dotenv().ok();
        Self {
            mongo_uri: env::var("MONGO_URI").expect("MONGO_URI not set"),
            jwt_secret: env::var("JWT_SECRET").expect("JWT_SECRET not set"),
        }
    }
}
