/// AES-256-GCM payload encryption, byte-compatible with the UI and the other
/// workers (same key, key id, encoding name and nonce|ciphertext|tag layout),
/// so the shared codec server at https://codec.tmprl-demo.cloud can decrypt it.
module MoneyTransfer.EncryptionCodec

open System
open System.Collections.Generic
open System.Security.Cryptography
open System.Text
open System.Threading.Tasks
open Google.Protobuf
open Temporalio.Api.Common.V1
open Temporalio.Converters

[<Literal>]
let DefaultKeyId = "test"

let defaultKey = Encoding.ASCII.GetBytes "sa-rocks!sa-rocks!sa-rocks!yeah!"

[<Literal>]
let private NonceSize = 12

[<Literal>]
let private TagSize = 16

let private encodingName = ByteString.CopyFromUtf8 "binary/encrypted"

let private encrypt (key: byte[]) (data: byte[]) =
    let bytes = Array.zeroCreate<byte> (NonceSize + data.Length + TagSize)
    let nonce = Span<byte>(bytes, 0, NonceSize)
    RandomNumberGenerator.Fill nonce
    use aes = new AesGcm(key, TagSize)
    aes.Encrypt(
        ReadOnlySpan<byte>(bytes, 0, NonceSize),
        ReadOnlySpan<byte>(data),
        Span<byte>(bytes, NonceSize, data.Length),
        Span<byte>(bytes, NonceSize + data.Length, TagSize)
    )
    bytes

let private decrypt (key: byte[]) (data: byte[]) =
    let plainLength = data.Length - NonceSize - TagSize
    let plain = Array.zeroCreate<byte> plainLength
    use aes = new AesGcm(key, TagSize)
    aes.Decrypt(
        ReadOnlySpan<byte>(data, 0, NonceSize),
        ReadOnlySpan<byte>(data, NonceSize, plainLength),
        ReadOnlySpan<byte>(data, NonceSize + plainLength, TagSize),
        Span<byte>(plain)
    )
    plain

type EncryptionCodec(?keyId: string, ?key: byte[]) =
    let keyId = defaultArg keyId DefaultKeyId
    let key = defaultArg key defaultKey
    let keyIdBytes = ByteString.CopyFromUtf8 keyId

    let encode (payload: Payload) =
        let encrypted = Payload(Data = ByteString.CopyFrom(encrypt key (payload.ToByteArray())))
        encrypted.Metadata["encoding"] <- encodingName
        encrypted.Metadata["encryption-key-id"] <- keyIdBytes
        encrypted

    let decode (payload: Payload) =
        match payload.Metadata.TryGetValue "encoding" with
        | true, encoding when encoding = encodingName ->
            match payload.Metadata.TryGetValue "encryption-key-id" with
            | true, id when id = keyIdBytes -> Payload.Parser.ParseFrom(decrypt key (payload.Data.ToByteArray()))
            | _, id -> invalidOp $"Unrecognized key ID {id}, expected {keyId}"
        | _ -> payload // not ours: pass through unchanged

    let mapAll f (payloads: IReadOnlyCollection<Payload>) =
        Task.FromResult<IReadOnlyCollection<Payload>>(payloads |> Seq.map f |> List<Payload>)

    interface IPayloadCodec with
        member _.EncodeAsync payloads = mapAll encode payloads
        member _.DecodeAsync payloads = mapAll decode payloads
