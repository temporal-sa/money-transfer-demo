using System.Text.Json.Serialization;

namespace MoneyTransfer;

public class ActivityInput
{
    [JsonPropertyName("idempotencyKey")]
    public string IdempotencyKey { get; set; }
    [JsonPropertyName("amount")]
    public float Amount { get; set; }
    [JsonPropertyName("type")]
    public string Type { get; set; }

    public ActivityInput()
    {
        IdempotencyKey = "";
        Amount = 0;
        Type = "";
    }

    public ActivityInput(string idempotencyKey, float amount, string type)
    {
        IdempotencyKey = idempotencyKey;
        Amount = amount;
        Type = type;
    }
}
