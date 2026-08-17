mod account_transfer_workflow;
mod account_transfer_workflow_scenarios;
mod activities;
mod shared;
mod codec;

use crate::account_transfer_workflow::AccountTransferWorkflow;
use crate::account_transfer_workflow_scenarios::{
    AccountTransferAdvancedVisibility, AccountTransferApiDowntime, AccountTransferHumanInLoop,
    AccountTransferInvalidAccount, AccountTransferRecoverableFailure,
};
use crate::activities::AccountTransferActivities;
use crate::codec::EncryptionCodec;
use crate::shared::TASK_QUEUE;
use std::time::Duration;
use temporalio_client::{
    Client, ClientKeepAliveOptions, ClientOptions, ClientTlsOptions, Connection, ConnectionOptions,
    TlsOptions,
};
use temporalio_common::data_converters::{
    DataConverter, DefaultFailureConverter, PayloadConverter,
};
use temporalio_common::telemetry::TelemetryOptions;
use temporalio_sdk::{Worker, WorkerOptions};
use temporalio_sdk_core::{CoreRuntime, RuntimeOptions};
use tracing::info;
use tracing_subscriber::EnvFilter;
use url::Url;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive(tracing::Level::INFO.into()))
        .init();

    let runtime = CoreRuntime::new_assume_tokio(
        RuntimeOptions::builder()
            .telemetry_options(TelemetryOptions::builder().build())
            .build()?,
    )?;

    let (conn_opts, namespace, is_cloud) = build_connection_options()?;
    let task_queue =
        std::env::var("TEMPORAL_TASK_QUEUE").unwrap_or_else(|_| TASK_QUEUE.to_string());

    let connection = Connection::connect(conn_opts).await?;
    if is_cloud {
        info!("Connected to Temporal Cloud!");
    } else {
        info!("Connected to local Temporal!");
    }

    // Optionally encrypt payloads via a data converter codec, gated on ENCRYPT_PAYLOADS
    let encrypt = std::env::var("ENCRYPT_PAYLOADS")
        .map(|v| v.eq_ignore_ascii_case("true"))
        .unwrap_or(false);
    let data_converter = if encrypt {
        info!("Encrypting payloads");
        DataConverter::new(
            PayloadConverter::default(),
            DefaultFailureConverter,
            EncryptionCodec,
        )
    } else {
        DataConverter::default()
    };

    let client = Client::new(
        connection,
        ClientOptions::new(namespace)
            .data_converter(data_converter)
            .build(),
    )?;

    let worker_options = WorkerOptions::new(task_queue)
        .register_workflow::<AccountTransferWorkflow>()?
        .register_workflow::<AccountTransferHumanInLoop>()?
        .register_workflow::<AccountTransferAdvancedVisibility>()?
        .register_workflow::<AccountTransferRecoverableFailure>()?
        .register_workflow::<AccountTransferApiDowntime>()?
        .register_workflow::<AccountTransferInvalidAccount>()?
        .register_activities(AccountTransferActivities)
        .build();

    let mut worker = Worker::new(&runtime, client, worker_options)?;
    worker.run().await?;

    Ok(())
}

/// Build connection options from environment variables.
///
/// Precedence: prefer a Cloud API key (which turns on TLS),
/// fall back to mTLS client cert/key files, otherwise connect in plaintext.
/// Returns the connection options, the resolved namespace, and whether TLS is enabled
fn build_connection_options()
-> Result<(ConnectionOptions, String, bool), Box<dyn std::error::Error>> {
    let address =
        std::env::var("TEMPORAL_ADDRESS").unwrap_or_else(|_| "127.0.0.1:7233".to_string());
    let namespace = std::env::var("TEMPORAL_NAMESPACE").unwrap_or_else(|_| "default".to_string());
    let cert_path = std::env::var("TEMPORAL_CERT_PATH").unwrap_or_default();
    let key_path = std::env::var("TEMPORAL_KEY_PATH").unwrap_or_default();
    let api_key = std::env::var("TEMPORAL_API_KEY").unwrap_or_default();
    // Optional SNI / server name override for TLS (e.g. when connecting through a proxy).
    let server_name = std::env::var("TEMPORAL_TLS_SERVER_NAME")
        .ok()
        .filter(|s| !s.is_empty());

    // Prefer API key auth, then mTLS, then plaintext.
    let (tls_options, api_key_opt) = if !api_key.is_empty() {
        info!("Using Cloud API key auth (address {address}, namespace {namespace})");
        (
            Some(TlsOptions {
                domain: server_name,
                ..Default::default()
            }),
            Some(api_key),
        )
    } else if !cert_path.is_empty() && !key_path.is_empty() {
        info!("Using mTLS auth");
        let tls = TlsOptions {
            domain: server_name,
            client_tls_options: Some(ClientTlsOptions {
                client_cert: std::fs::read(&cert_path)?,
                client_private_key: std::fs::read(&key_path)?,
            }),
            ..Default::default()
        };
        (Some(tls), None)
    } else {
        (None, None)
    };

    // TLS being enabled implies a Cloud/secure connection; plaintext implies local.
    let is_cloud = tls_options.is_some();
    let target = parse_address(&address, is_cloud)?;

    let conn_opts = ConnectionOptions::new(target)
        .maybe_tls_options(tls_options)
        .maybe_api_key(api_key_opt)
        // Send HTTP/2 keep-alive pings so the connection stays warm during idle waits
        // (e.g. human-in-the-loop workflows parked on an approval) and isn't reaped by the
        // server or a Cloud load balancer.
        .keep_alive(Some(ClientKeepAliveOptions {
            interval: Duration::from_secs(10),
            timeout: Duration::from_secs(10),
        }))
        .build();

    Ok((conn_opts, namespace, is_cloud))
}

/// Parse an address into a Url, prepending a scheme when the address is a bare `host:port`.
/// When no scheme is present, use `https` if TLS is enabled, otherwise `http`.
fn parse_address(address: &str, use_tls: bool) -> Result<Url, Box<dyn std::error::Error>> {
    // `Url::parse("localhost:7233")` treats `localhost` as the scheme and yields no host, so only
    // accept a direct parse that actually has a host (i.e. the address already had a scheme).
    if let Ok(url) = Url::parse(address)
        && url.host().is_some()
    {
        return Ok(url);
    }
    let scheme = if use_tls { "https" } else { "http" };
    Ok(Url::parse(&format!("{scheme}://{address}"))?)
}
