use mongodb::{options::ClientOptions, Client};
use std::env;

pub async fn init() -> mongodb::error::Result<Client> {
    let uri = env::var("MONGO_URI").expect("MONGO_URI must be set");
    let options = ClientOptions::parse(uri).await?;
    Client::with_options(options)
}
