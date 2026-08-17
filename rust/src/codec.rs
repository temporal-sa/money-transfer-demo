//! AES-256-GCM payload codec, matching the money-transfer-demo codecs in the other SDKs

use aes_gcm::aead::{Aead, AeadCore, KeyInit, OsRng};
use aes_gcm::{Aes256Gcm, Key, Nonce};
use futures::{FutureExt, future::BoxFuture};
use prost::Message;
use std::collections::HashMap;
use temporalio_common::data_converters::{PayloadCodec, SerializationContextData, PayloadConversionError};
use temporalio_common::protos::temporal::api::common::v1::Payload;
use tracing::error;

pub struct EncryptionCodec;

impl EncryptionCodec {
    const KEY: &[u8; 32] = b"sa-rocks!sa-rocks!sa-rocks!yeah!";
    const KEY_ID: &str = "test";
    const ENCODING: &[u8] = b"binary/encrypted";

    fn cipher() -> Aes256Gcm {
        Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(Self::KEY))
    }

    fn encode_payload(payload: Payload) -> Result<Payload, PayloadConversionError> {
        let plaintext = payload.encode_to_vec();
        let nonce = Aes256Gcm::generate_nonce(&mut OsRng);
        let ciphertext = match Self::cipher().encrypt(&nonce, plaintext.as_ref()) {
            Ok(data) => {
                data
            }
            Err(err) => {
                error!("Failed to encode data: {:?}", err);
                let codec_error = format!("{:?}", err);
                return Err(PayloadConversionError::EncodingError(
                    codec_error.into(),
                ));
            }
        };
        let mut data = nonce.to_vec();
        data.extend_from_slice(&ciphertext);

        let mut metadata = HashMap::new();
        metadata.insert("encoding".to_string(), Self::ENCODING.to_vec());
        metadata.insert(
            "encryption-key-id".to_string(),
            Self::KEY_ID.as_bytes().to_vec(),
        );
        Ok(Payload {
            metadata,
            data,
            ..Default::default()
        })
    }

    fn decode_payload(payload: Payload) -> Result<Payload, PayloadConversionError> {
        if payload.metadata.get("encoding").map(Vec::as_slice) != Some(Self::ENCODING) {
            return Ok(payload);
        }
        let (nonce_bytes, ciphertext) = payload.data.split_at(12);
        let plaintext = match Self::cipher().decrypt(Nonce::from_slice(nonce_bytes), ciphertext) {
            Ok(data) => data,
            Err(err) => {
                error!("Failed to decode payload: {:?}", err);
                let codec_error = format!("{:?}", err);
                return Err(PayloadConversionError::EncodingError(
                    codec_error.into()
                ));
            }
        };
        match Payload::decode(plaintext.as_slice()) {
            Ok(decoded_payload) => Ok(decoded_payload),
            Err(decode_err) => {
                error!("Failed to parse decrypted bytes into Payload: {:?}", decode_err);
                let codec_error = format!("Protobuf parsing failed: {:?}", decode_err);
                return Err(PayloadConversionError::EncodingError(
                    codec_error.into()
                ));
            }
        }

    }
}

impl PayloadCodec for EncryptionCodec {
    fn encode(
        &self,
        _: &SerializationContextData,
        payloads: Vec<Payload>,
    ) -> BoxFuture<'static, Result<Vec<Payload>, PayloadConversionError>> {
        async move { payloads.into_iter().map(Self::encode_payload).collect() }.boxed()
    }

    fn decode(
        &self,
        _: &SerializationContextData,
        payloads: Vec<Payload>,
    ) -> BoxFuture<'static, Result<Vec<Payload>, PayloadConversionError>> {
        async move { payloads.into_iter().map(Self::decode_payload).collect() }.boxed()
    }
}
