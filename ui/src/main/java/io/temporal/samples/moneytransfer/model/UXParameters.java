package io.temporal.samples.moneytransfer.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class UXParameters {
    private int amount;
    private String fromAccount;
    private String toAccount;
    private ExecutionScenario scenario;

    public TransferInput toTransferInput() {
        return new TransferInput(this.amount,
                fromAccount != null ? fromAccount : "fromAccount", toAccount != null ? toAccount : "toAccount");
    }
}
