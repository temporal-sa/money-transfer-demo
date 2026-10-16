package io.temporal.samples.moneytransfer.helper;

import java.util.HashMap;
import java.util.Map;

public class ServerInfo {

    public static String getCertPath() {
        return getEnv("TEMPORAL_CERT_PATH", "");
    }

    public static String getKeyPath() {
        // check first for a specific pkcs8 env var, if null/empty then check for generic env var
        String keyPath = System.getenv("TEMPORAL_KEY_PKCS8_PATH");
        return keyPath != null && !keyPath.isEmpty() ? keyPath : getEnv("TEMPORAL_KEY_PATH", "");
    }

    public static String getNamespace() {
        return getEnv("TEMPORAL_NAMESPACE", "default");
    }

    public static String getAddress() {
        return getEnv("TEMPORAL_ADDRESS", "localhost:7233");
    }

    public static String getTaskqueue() {
        return getEnv("TEMPORAL_MONEYTRANSFER_TASKQUEUE", "MoneyTransfer");
    }

    public static String getApiKey() {
      return getEnv("TEMPORAL_API_KEY", "");
    }

    // Opt-in for a local server on a non-default address, e.g. a dev server on another port
    public static boolean getAllowPlaintext() {
        return getEnv("TEMPORAL_ALLOW_PLAINTEXT", "false").equalsIgnoreCase("true");
    }

    public static int getWorkflowSleepDuration() {
        String workflowSleepDurationString = getEnv("TEMPORAL_MONEYTRANSFER_SLEEP", "0");
        int workflowSleepDuration = 0;
        try {
            workflowSleepDuration = Integer.parseInt(workflowSleepDurationString);
        } catch (NumberFormatException e) {
            System.err.println("Error parsing environment variable as an integer: " + e.getMessage());
        }
        return workflowSleepDuration != 0 ? workflowSleepDuration : 5;
    }

    public static Map<String, String> getServerInfo() {
        Map<String, String> info = new HashMap<>();
        info.put("namespace", getNamespace());
        info.put("address", getAddress());
        info.put("taskQueue", getTaskqueue());
        if (getApiKey().isEmpty()) {
            info.put("certPath", getCertPath());
            info.put("keyPath", getKeyPath());
        } else {
            if (getApiKey().length() <= 8) {
              info.put("apiKey", getApiKey());
            } else {
              info.put("apiKey",
                  getApiKey().substring(0, 4) +
                  "..." +
                  getApiKey().substring(getApiKey().length()-4)
              );
            }
        }
        return info;
    }

    private static String getEnv(String key, String defaultValue) {
        String value = System.getenv(key);
        return value != null && !value.isEmpty() ? value : defaultValue;
    }
}
